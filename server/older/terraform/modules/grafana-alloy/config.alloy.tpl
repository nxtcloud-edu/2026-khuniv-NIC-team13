%{ for target in scrape_targets ~}
prometheus.scrape "${target.name}" {
  targets = [{
    __address__ = "${target.address}",
  }]
  forward_to      = [prometheus.remote_write.grafana_cloud.receiver]
  metrics_path    = "${target.metrics_path}"
  scrape_interval = "${target.scrape_interval}"
}

%{ endfor ~}
prometheus.remote_write "grafana_cloud" {
  endpoint {
    url = env("GRAFANA_CLOUD_PROMETHEUS_ENDPOINT")

    basic_auth {
      username = env("GRAFANA_CLOUD_PROMETHEUS_USERNAME")
      password = env("GRAFANA_CLOUD_API_KEY")
    }
  }
}
