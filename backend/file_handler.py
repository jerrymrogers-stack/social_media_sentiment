# file_handler.py
# File ingestion and validation for the Social Media Analytics Tool

import os
import json
import pandas as pd
from datetime import datetime


class FileHandler:

    # ---------------------------------------------------------------------------
    # COLUMN DEFINITIONS
    # Centralized here so validation and cleaning stay in sync automatically.
    # ---------------------------------------------------------------------------

    REQUIRED_COLUMNS = ['username', 'post_text', 'post_date']

    OPTIONAL_COLUMNS = [
        'display_name', 'bio', 'followers_count', 'following_count',
        'account_age_days', 'likes', 'comments', 'shares'
    ]

    # Default values applied to missing optional columns and NaN cells
    COLUMN_DEFAULTS = {
        'display_name':    None,   # None = fall back to username (handled in clean_data)
        'bio':             '',
        'followers_count': 0,
        'following_count': 0,
        'account_age_days': 365,
        'likes':           0,
        'comments':        0,
        'shares':          0,
        'post_text':       '',
    }

    # Columns that should be cast to int after filling NaN
    INT_COLUMNS = [
        'followers_count', 'following_count', 'account_age_days',
        'likes', 'comments', 'shares'
    ]

    SUPPORTED_FORMATS = ['csv', 'json', 'xlsx']

    # ---------------------------------------------------------------------------
    # PUBLIC ENTRY POINT
    # ---------------------------------------------------------------------------

    @classmethod
    def load_file(cls, file_path: str) -> pd.DataFrame | None:
        """
        Main entry point. Detects format, parses, validates, and cleans.
        Returns a clean DataFrame or None on any failure.
        """
        fmt = cls.get_file_format(file_path)
        if not fmt:
            print(f"✗ Unsupported or unrecognized file format: '{file_path}'")
            return None

        parsers = {
            'csv':  cls.parse_csv,
            'json': cls.parse_json,
            'xlsx': cls.parse_excel,
        }

        df = parsers[fmt](file_path)
        if df is None:
            return None

        if not cls.validate_columns(df):
            return None

        return cls.clean_data(df)

    # ---------------------------------------------------------------------------
    # PARSERS
    # ---------------------------------------------------------------------------

    @staticmethod
    def parse_csv(file_path: str) -> pd.DataFrame | None:
        """Parse a CSV file into a DataFrame."""
        try:
            df = pd.read_csv(file_path)
            print(f"✓ CSV loaded: {len(df)} rows")
            return df
        except Exception as e:
            print(f"✗ Error parsing CSV: {e}")
            return None

    @staticmethod
    def parse_json(file_path: str) -> pd.DataFrame | None:
        """
        Parse a JSON file into a DataFrame.
        Accepts both a JSON array (list of records) or a single object.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            records = data if isinstance(data, list) else [data]
            df = pd.DataFrame(records)
            print(f"✓ JSON loaded: {len(df)} rows")
            return df
        except Exception as e:
            print(f"✗ Error parsing JSON: {e}")
            return None

    @staticmethod
    def parse_excel(file_path: str) -> pd.DataFrame | None:
        """Parse an Excel (.xlsx) file into a DataFrame."""
        try:
            df = pd.read_excel(file_path)
            print(f"✓ Excel loaded: {len(df)} rows")
            return df
        except Exception as e:
            print(f"✗ Error parsing Excel: {e}")
            return None

    # ---------------------------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------------------------

    @classmethod
    def validate_columns(cls, df: pd.DataFrame) -> bool:
        """
        Confirm all required columns are present.
        Warns about missing optional columns but does not fail on them.
        """
        missing_required = [c for c in cls.REQUIRED_COLUMNS if c not in df.columns]
        if missing_required:
            print(f"✗ Missing required columns: {missing_required}")
            return False

        missing_optional = [c for c in cls.OPTIONAL_COLUMNS if c not in df.columns]
        if missing_optional:
            print(f"  ℹ Optional columns not present (will use defaults): {missing_optional}")

        print(f"✓ Column validation passed")
        return True

    # ---------------------------------------------------------------------------
    # CLEANING
    # ---------------------------------------------------------------------------

    @classmethod
    def clean_data(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize and clean the DataFrame:
          - Add missing optional columns with defaults
          - Fill NaN values
          - Cast numeric columns
          - Parse and validate post_date
          - Drop rows with unparseable dates
        """
        # Add any missing optional columns with their defaults
        for col, default in cls.COLUMN_DEFAULTS.items():
            if col not in df.columns:
                df[col] = default

        # display_name falls back to username if missing or blank
        mask = df['display_name'].isna() | (df['display_name'].astype(str).str.strip() == '')
        df.loc[mask, 'display_name'] = df.loc[mask, 'username']

        # Fill remaining NaN values using the defaults map
        fill_values = {k: v for k, v in cls.COLUMN_DEFAULTS.items() if v is not None}
        df = df.fillna(fill_values)

        # Parse post_date — coerce bad values to NaT, then drop those rows
        df['post_date'] = pd.to_datetime(df['post_date'], errors='coerce')
        invalid_dates = df['post_date'].isna().sum()
        if invalid_dates:
            print(f"  ⚠ Dropped {invalid_dates} rows with unparseable dates")
        df = df.dropna(subset=['post_date'])

        # Cast numeric columns to int (coerce bad values to 0 first)
        for col in cls.INT_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        print(f"✓ Data cleaned: {len(df)} valid rows remaining")
        return df

    # ---------------------------------------------------------------------------
    # UTILITY
    # ---------------------------------------------------------------------------

    @classmethod
    def get_file_format(cls, file_path: str) -> str | None:
        """
        Extract and validate the file extension.
        Returns the format string or None if unsupported.
        """
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        return ext if ext in cls.SUPPORTED_FORMATS else None

    @classmethod
    def summarize(cls, df: pd.DataFrame):
        """
        Print a quick summary of a loaded DataFrame.
        Useful for debugging during development.
        """
        print(f"\n--- File Summary ---")
        print(f"  Rows:     {len(df)}")
        print(f"  Columns:  {list(df.columns)}")
        print(f"  Date range: {df['post_date'].min()} → {df['post_date'].max()}")
        print(f"  Unique users: {df['username'].nunique()}")
        print(f"--------------------\n")