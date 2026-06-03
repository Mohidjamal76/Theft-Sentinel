import re
from urllib.parse import urlparse

from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


USERNAME_ERROR = (
    "Username must be 3-30 characters, start with a letter, and contain only "
    "letters, numbers, dots, or underscores."
)
EMAIL_ERROR = "Enter a valid email address."
PASSWORD_ERROR = (
    "Password must be at least 8 characters and include uppercase, lowercase, "
    "number, and special character."
)
PHONE_ERROR = "Enter a valid Pakistani mobile number (e.g., 03001234567)."
CNIC_ERROR = "Enter a valid CNIC (e.g., 35202-1234567-1)."
NAME_ERROR = "Name must contain only letters and be at least 2 characters long."
COMPANY_ERROR = "Company name is required."
ADDRESS_ERROR = "Address is required and must be at least 10 characters."
REASON_ERROR = "Please provide a detailed reason (minimum 10 characters)."


USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.]{2,29}$")
PHONE_PATTERN = re.compile(r"^(\+92|92|0)3[0-9]{9}$")
CNIC_PATTERN = re.compile(r"^\d{5}-?\d{7}-?\d{1}$")
NAME_PATTERN = re.compile(r"^[A-Za-z .-]+$")
COMPANY_PATTERN = re.compile(r"^[A-Za-z0-9 .&-]+$")
STREAM_SCHEMES = {"rtsp", "rtmp", "http", "https"}


def clean_text(value, field_name="value", min_length=1, max_length=None, message=None):
    value = "" if value is None else str(value).strip()
    if not value or len(value) < min_length:
        raise serializers.ValidationError(message or f"{field_name} is required.")
    if max_length is not None and len(value) > max_length:
        raise serializers.ValidationError(f"{field_name} must be at most {max_length} characters.")
    return value


def normalize_username(value):
    value = clean_text(value, "Username", 3, 30, USERNAME_ERROR)
    if not USERNAME_PATTERN.match(value):
        raise serializers.ValidationError(USERNAME_ERROR)
    return value


def normalize_email(value):
    value = clean_text(value, "Email", 1, 255, EMAIL_ERROR).lower()
    if " " in value:
        raise serializers.ValidationError(EMAIL_ERROR)
    try:
        EmailValidator(message=EMAIL_ERROR)(value)
    except DjangoValidationError:
        raise serializers.ValidationError(EMAIL_ERROR)
    return value


def validate_password_value(value):
    if value is None:
        raise serializers.ValidationError(PASSWORD_ERROR)
    value = str(value)
    if (
        len(value) < 8
        or len(value) > 128
        or re.search(r"\s", value)
        or not re.search(r"[A-Z]", value)
        or not re.search(r"[a-z]", value)
        or not re.search(r"[0-9]", value)
        or not re.search(r"[^A-Za-z0-9\s]", value)
    ):
        raise serializers.ValidationError(PASSWORD_ERROR)
    return value


def normalize_pakistani_phone(value, required=True):
    if value is None or str(value).strip() == "":
        if required:
            raise serializers.ValidationError(PHONE_ERROR)
        return ""
    value = str(value).strip()
    if not PHONE_PATTERN.match(value):
        raise serializers.ValidationError(PHONE_ERROR)
    if value.startswith("+92"):
        return value
    if value.startswith("92"):
        return f"+{value}"
    return f"+92{value[1:]}"


def normalize_cnic(value):
    value = clean_text(value, "CNIC", 13, 20, CNIC_ERROR)
    digits = re.sub(r"[\s-]+", "", value)
    if not digits.isdigit():
        raise serializers.ValidationError(CNIC_ERROR)
    if len(digits) != 13:
        raise serializers.ValidationError(CNIC_ERROR)
    return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"


def validate_name(value):
    value = clean_text(value, "Name", 2, 100, NAME_ERROR)
    if not NAME_PATTERN.match(value) or value.replace(".", "").replace("-", "").strip().isdigit():
        raise serializers.ValidationError(NAME_ERROR)
    return value


def validate_company_name(value):
    value = clean_text(value, "Company name", 2, 150, COMPANY_ERROR)
    if not COMPANY_PATTERN.match(value):
        raise serializers.ValidationError(COMPANY_ERROR)
    return value


def validate_address(value):
    return clean_text(value, "Address", 10, 300, ADDRESS_ERROR)


def validate_reason(value):
    return clean_text(value, "Reason", 10, 1000, REASON_ERROR)


def validate_message(value, min_length=10, max_length=5000):
    return clean_text(value, "Message", min_length, max_length, f"Message must be at least {min_length} characters.")


def validate_short_text(value, field_name, min_length=2, max_length=150):
    return clean_text(value, field_name, min_length, max_length, f"{field_name} is required.")


def validate_camera_name(value):
    return validate_short_text(value, "Camera name", 2, 100)


def validate_camera_location(value):
    return validate_short_text(value, "Location", 2, 150)


def validate_stream_url(value):
    value = clean_text(value, "Stream URL", 1, 512, "Enter a valid camera stream URL.")
    parsed = urlparse(value)
    if parsed.scheme not in STREAM_SCHEMES or not parsed.netloc:
        raise serializers.ValidationError("Stream URL must start with rtsp://, rtmp://, http://, or https://.")
    return value
