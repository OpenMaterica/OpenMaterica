# SPDX-License-Identifier: Apache-2.0
"""OpenMaterica: material records and the reader of their specification (`docs/specification/`)."""

from materica.core.build import check_build
from materica.core.hashing import content_hash
from materica.core.read import read
from materica.io.plain import load_records

__all__ = ["check_build", "content_hash", "load_records", "read"]
