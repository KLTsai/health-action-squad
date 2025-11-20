"""Main entry point for Health Action Squad.

Usage:
    python main.py --input path/to/health_report.json
    python main.py --input path/to/health_report.json --profile path/to/user_profile.json
"""

import argparse
import json
import sys
from pathlib import Path

from src.core.orchestrator import Orchestrator
from src.core.config import Config
from src.utils.logger import get_logger


logger = get_logger(__name__)


def load_json_file(file_path: str) -> dict:
    """Load JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_output(data: dict, output_path: Path) -> None:
    """Save output to file.

    Args:
        data: Data to save
        output_path: Output file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Output saved to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Health Action Squad - AI Health Concierge"
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to health report JSON file"
    )
    parser.add_argument(
        "--profile",
        "-p",
        help="Path to user profile JSON file (optional)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Path to output file (default: output/result_<timestamp>.json)"
    )

    args = parser.parse_args()

    try:
        # Load input data
        logger.info(f"Loading health report from: {args.input}")
        health_report = load_json_file(args.input)

        user_profile = None
        if args.profile:
            logger.info(f"Loading user profile from: {args.profile}")
            user_profile = load_json_file(args.profile)

        # Initialize orchestrator
        logger.info("Initializing orchestrator")
        orchestrator = Orchestrator()

        # Execute workflow
        logger.info("Starting workflow execution")
        result = orchestrator.execute(
            health_report=health_report,
            user_profile=user_profile
        )

        # Save output
        if args.output:
            output_path = Path(args.output)
        else:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Config.OUTPUT_DIR / f"result_{timestamp}.json"

        save_output(result, output_path)

        # Print summary
        print("\n" + "=" * 60)
        print("Health Action Squad - Execution Summary")
        print("=" * 60)
        print(f"Session ID: {result['session_id']}")
        print(f"Status: {result['status']}")
        print(f"Risk Tags: {', '.join(result.get('risk_tags', []))}")
        print(f"Iterations: {result.get('iterations', 1)}")
        print(f"Output saved to: {output_path}")
        print("=" * 60)

        # Print plan preview
        plan = result.get('plan', '')
        if plan:
            print("\nGenerated Plan (preview):")
            print("-" * 60)
            # Show first 500 characters
            preview = plan[:500] + "..." if len(plan) > 500 else plan
            print(preview)
            print("-" * 60)

        logger.info("Workflow completed successfully")
        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        print(f"Error: Invalid JSON file - {e}", file=sys.stderr)
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
