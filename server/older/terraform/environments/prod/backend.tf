terraform {
  cloud {
    organization = "pertineo"

    workspaces {
      name = "pertineo-prod"
    }
  }
}

