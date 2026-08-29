package com.example.demo.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "pertineo.session")
public class PertineoSessionProperties {

    private int ttlMinutes;
    private int extendFixedMinutes;
    private String cookieName;
    private String cookiePath;
    private String sameSite;
    private boolean secure;
}

