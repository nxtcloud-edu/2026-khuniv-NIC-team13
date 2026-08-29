terraform {
  cloud {
    organization = "pertino"

    workspaces {
      name = "pertino-dev"
    }
  }
}

