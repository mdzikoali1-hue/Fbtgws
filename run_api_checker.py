import getpass
import os
import time
from pathlib import Path

import requests

API_URL = "https://api.ekycpro.com/v1/check"
SERVICE_TYPES = {
    "1": ("Facebook", "facebook"),
    "2": ("WhatsApp", "ws"),
    "3": ("Telegram", "telegram"),
}

def read_numbers():
    print("\nPaste your own or authorized phone numbers, one per line.")
    print("Type DONE on a new line when finished.\n")
    numbers = []
    seen = set()
    while True:
        try:
            line = input()
        except EOFError:
            break
        line = "".join(line.split())
        if line.upper() == "DONE":
            break
        if line and line not in seen:
            seen.add(line)
            numbers.append(line)
    return numbers

def main():
    print("=" * 44)
    print("        eKYCPro SINGLE-SERVICE CHECKER")
    print("=" * 44)
    for key, (label, _) in SERVICE_TYPES.items():
        print(f"{key}. {label}")
    choice = input("Select service: ").strip()
    if choice not in SERVICE_TYPES:
        print("Invalid service selection.")
        return

    label, service_type = SERVICE_TYPES[choice]
    api_key = os.getenv("EKYCPRO_API_KEY") or getpass.getpass(
        "eKYCPro API key (hidden): "
    ).strip()
    if not api_key:
        print("API key is required.")
        return

    numbers = read_numbers()
    if not numbers:
        print("No numbers entered.")
        return

    registered = []
    unregistered = []
    errors = []

    print(f"\nChecking {len(numbers)} entries with {label}...")
    print("Use only numbers you own or are authorized to verify.")
    for index, number in enumerate(numbers, start=1):
        if not number.startswith("+") or not number[1:].isdigit():
            errors.append(f"{number}\tINVALID_FORMAT")
            print(f"[{index}/{len(numbers)}] Invalid international format: {number}")
            continue

        try:
            response = requests.post(
                API_URL,
                headers={
                    "X-API-Key": api_key,
                    "Content-Type": "application/json",
                },
                json={"service_type": service_type, "identifier": number},
                timeout=30,
            )
            try:
                result = response.json()
            except ValueError:
                errors.append(f"{number}\tHTTP_{response.status_code}\tNON_JSON_RESPONSE")
                print(f"[{index}/{len(numbers)}] API returned a non-JSON response.")
                continue

            if not response.ok or result.get("success") is not True:
                errors.append(f"{number}\tHTTP_{response.status_code}\t{result}")
                print(f"[{index}/{len(numbers)}] API error for {number} (see Errors.txt)")
                continue

            data = result.get("data") or {}
            status = data.get("registered")
            strategy = result.get("pricingStrategy")

            if status is True and strategy != "FREE":
                registered.append(number)
                print(f"[{index}/{len(numbers)}] Registered: {number}")
            elif status is False and strategy != "FREE":
                unregistered.append(number)
                print(f"[{index}/{len(numbers)}] Unregistered: {number}")
            else:
                errors.append(f"{number}\tUNDETERMINED\t{result}")
                print(f"[{index}/{len(numbers)}] Undetermined: {number} (see Errors.txt)")

        except requests.RequestException as exc:
            errors.append(f"{number}\tREQUEST_ERROR\t{exc}")
            print(f"[{index}/{len(numbers)}] Request failed for {number}.")

        # Gentle pacing; check your provider's rate limits and pricing.
        if index < len(numbers):
            time.sleep(1)

    Path("Register.txt").write_text(
        "".join(number + "\n" for number in registered), encoding="utf-8"
    )
    Path("Unregistered.txt").write_text(
        "".join(number + "\n" for number in unregistered), encoding="utf-8"
    )
    Path("Errors.txt").write_text(
        "".join(line + "\n" for line in errors), encoding="utf-8"
    )

    print("\nFinished. Results saved in the current directory:")
    print(f"Register.txt: {len(registered)}")
    print(f"Unregistered.txt: {len(unregistered)}")
    print(f"Errors.txt: {len(errors)}")
    print("Checks may be billed by the provider.")

if __name__ == "__main__":
    main()
