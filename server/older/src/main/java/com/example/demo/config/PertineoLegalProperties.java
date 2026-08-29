package com.example.demo.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "pertineo.legal")
public class PertineoLegalProperties {

    private String termsVersion = "2026-03-01";
    private String privacyCollectionVersion = "2026-03-01";
    private String privacyPolicyVersion = "2026-03-01";
    private String thirdPartyVersion = "2026-03-01";
}

