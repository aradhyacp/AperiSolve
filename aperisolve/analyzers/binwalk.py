"""Binwalk Analyzer for Image Submissions."""

import shutil
import subprocess
from pathlib import Path

from .utils import MAX_PENDING_TIME, update_data


def analyze_binwalk(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using binwalk."""

    image_name = input_img.name
    extracted_dir = output_dir / f"_{image_name}.extracted"

    try:
        # Run binwalk
        data = subprocess.run(
            ["binwalk", "-e", "../" + str(image_name), "--run-as=root"],
            cwd=output_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )
        binwalk_stderr = data.stderr

        # Track whether extraction happened
        extraction_occurred = extracted_dir.exists()

        zip_exist = False
        zip_stderr = ""
        if extraction_occurred:
            # Zip extracted files
            zip_data = subprocess.run(
                ["7z", "a", "../binwalk.7z", "*"],
                cwd=extracted_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=MAX_PENDING_TIME,
            )
            zip_stderr = zip_data.stderr
            # Only set zip_exist if 7z succeeded (return code 0)
            if zip_data.returncode == 0:
                zip_exist = True

        # Remove the extracted directory
        if extracted_dir.exists():
            shutil.rmtree(extracted_dir)

        # Report errors appropriately:
        # 1. If binwalk had errors and didn't extract anything, report binwalk error
        # 2. If extraction occurred but 7z failed, report 7z error
        error_messages = []
        if binwalk_stderr and not extraction_occurred:
            error_messages.append(f"Binwalk: {binwalk_stderr}")
        if extraction_occurred and not zip_exist:
            if zip_stderr:
                error_messages.append(f"7z compression: {zip_stderr}")
            else:
                error_messages.append("7z compression failed with no error output")

        if error_messages:
            err = {
                "binwalk": {
                    "status": "error",
                    "error": "\n".join(error_messages),
                }
            }
            update_data(output_dir, err)
            return None

        output_data = {
            "binwalk": {
                "status": "ok",
                "output": data.stdout.split("\n") if data else [],
            }
        }
        if zip_exist:
            output_data["binwalk"]["download"] = f"/download/{output_dir.name}/binwalk"

        update_data(output_dir, output_data)

    except Exception as e:
        update_data(output_dir, {"binwalk": {"status": "error", "error": str(e)}})
    return None
