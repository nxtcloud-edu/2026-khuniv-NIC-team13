"""Keep tests isolated from deployment environment configuration."""

import os

os.environ["DEBUG"] = "false"
os.environ["REPOSITORY_BACKEND"] = "memory"
os.environ["EMAIL_DELIVERY_BACKEND"] = "disabled"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "1234"
