"""Gradio UI for converting receipt images to Markdown or JSON using llama.cpp."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

import gradio as gr

from llama_client import LlamaClient, LlamaConfig
from prompts import JSON_INSTRUCTION, JSON_REPAIR_PROMPT, MARKDOWN_INSTRUCTION
from receipt_io import (
    ReceiptGroup,
    build_outputs_zip,
    discover_receipts,
    encode_image_to_data_url,
    prepare_workdir,
    safe_extract_zip,
    write_output,
    list_receipt_table,
)


def load_zip(zip_file: gr.File) -> Tuple[List[List[str | int]], str, List[ReceiptGroup], str]:
    if zip_file is None:
        raise gr.Error("Please upload a ZIP file containing receipts.")

    tempdir_path = prepare_workdir()
    try:
        safe_extract_zip(zip_file.name, tempdir_path)
        receipts = discover_receipts(tempdir_path)
        if not receipts:
            raise gr.Error("No receipt folders with PNG pages were found in the ZIP.")
        table = list_receipt_table(receipts)
        return table, tempdir_path, receipts, "Upload complete"
    except Exception as exc:  # pragma: no cover - UI surface
        shutil.rmtree(tempdir_path, ignore_errors=True)
        raise gr.Error(f"Failed to process ZIP: {exc}")


def _build_prompt(receipt: ReceiptGroup, output_format: str) -> str:
    base = MARKDOWN_INSTRUCTION if output_format == "markdown" else JSON_INSTRUCTION
    guidance = (
        "This is ONE receipt/invoice spanning multiple pages; "
        "preserve reading order; do not hallucinate; if a field is missing, use null or leave blank appropriately. "
        f"Document name: {receipt.name}."
    )
    return f"{base}\n\n{guidance}"


def _run_model(llama: LlamaClient, receipt: ReceiptGroup, output_format: str) -> str:
    images = [encode_image_to_data_url(p) for p in receipt.pages]
    prompt = _build_prompt(receipt, output_format)
    if output_format == "markdown":
        return llama.chat_markdown(prompt, images)

    response = llama.chat_json(prompt, images)
    try:
        json.loads(response)
        return response
    except json.JSONDecodeError:
        repair_prompt = JSON_REPAIR_PROMPT
        repaired = llama.chat_json(f"{repair_prompt}\n\n{response}", images=[])
        return repaired


def convert_selected(tempdir: str, selected: List[str], output_format: str) -> Tuple[str, str]:
    if not tempdir:
        raise gr.Error("Upload a ZIP first.")
    receipts = discover_receipts(tempdir)
    if not selected:
        raise gr.Error("Select at least one receipt.")

    receipt_map: Dict[str, ReceiptGroup] = {r.name: r for r in receipts}
    llama = LlamaClient(LlamaConfig())
    output_dir = Path(tempdir) / "outputs"

    last_preview = ""
    for name in selected:
        receipt = receipt_map.get(name)
        if not receipt:
            continue
        result = _run_model(llama, receipt, output_format)
        output_path = write_output(receipt.name, result, output_format, output_dir)
        last_preview = f"# {receipt.name}\n\n" + result[:5000]

    zip_path = build_outputs_zip(output_dir, Path(tempdir) / "outputs.zip")
    return last_preview, str(zip_path)


def preview_receipt(tempdir: str, selected: List[str]):
    if not tempdir or not selected:
        return None
    receipts = discover_receipts(tempdir)
    receipt_map = {r.name: r for r in receipts}
    receipt = receipt_map.get(selected[0]) if selected else None
    if not receipt:
        return None
    return [str(p) for p in receipt.pages]


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Receipt to Markdown/JSON") as demo:
        gr.Markdown("# Receipt/Invoice Converter")
        with gr.Row():
            zip_file = gr.File(label="Upload ZIP", file_types=[".zip"], type="filepath")
            status = gr.Textbox(label="Status", interactive=False)
        tempdir_state = gr.State("")

        with gr.Row():
            table = gr.Dataframe(headers=["Receipt", "Pages"], datatype=["str", "number"], label="Receipts", interactive=False)
            gallery = gr.Gallery(label="Preview", allow_preview=True, show_label=True)

        with gr.Row():
            selected = gr.CheckboxGroup(label="Select receipts to convert")
            output_format = gr.Radio(["markdown", "json"], label="Output format", value="markdown")

        with gr.Row():
            btn_selected = gr.Button("Convert selected")
            btn_all = gr.Button("Convert all")

        progress = gr.Textbox(label="Progress", interactive=False)
        preview = gr.Markdown(label="Preview")
        download = gr.File(label="Download outputs ZIP")

        def on_upload(file):
            table_data, tempdir, receipts, msg = load_zip(file)
            return table_data, [r.name for r in receipts], tempdir, msg

        zip_file.upload(
            on_upload,
            inputs=[zip_file],
            outputs=[table, selected, tempdir_state, status],
        )

        def on_select(tempdir, selected_names):
            return preview_receipt(tempdir, selected_names)

        selected.change(on_select, inputs=[tempdir_state, selected], outputs=gallery)

        def run_conversion(tempdir, selected_names, fmt):
            progress_msg = f"Converting {len(selected_names)} receipt(s)..."
            prev, zip_out = convert_selected(tempdir, selected_names, fmt)
            return progress_msg, prev, zip_out

        btn_selected.click(
            run_conversion,
            inputs=[tempdir_state, selected, output_format],
            outputs=[progress, preview, download],
        )

        def run_all(tempdir, fmt):
            if not tempdir:
                raise gr.Error("Upload a ZIP first.")
            receipts = discover_receipts(tempdir)
            names = [r.name for r in receipts]
            return run_conversion(tempdir, names, fmt)

        btn_all.click(
            run_all,
            inputs=[tempdir_state, output_format],
            outputs=[progress, preview, download],
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch()
