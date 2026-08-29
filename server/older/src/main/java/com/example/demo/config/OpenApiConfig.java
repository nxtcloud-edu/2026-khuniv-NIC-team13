package com.example.demo.config;

import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.info.Info;
import io.swagger.v3.oas.annotations.info.License;
import io.swagger.v3.oas.annotations.servers.Server;
import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@OpenAPIDefinition(
        info = @Info(
                title = "Pertineo API",
                description = "역량분석/이력서 서비스 API 문서",
                version = "v1.0.0",
                license = @License(name = "Apache 2.0")
        ),
        servers = {
                @Server(
                        url = "${pertineo.openapi.dev-server-url:https://khu-pertineo-deploy.com}",
                        description = "개발 서버"
                ),
                @Server(url = "http://localhost:8080", description = "로컬 서버")
        }
)
@Configuration
public class OpenApiConfig {

    private static final String[] V2_API_PACKAGES = {
            "com.example.demo.analysis.api.v2",
            "com.example.demo.autocomplete.api.v2",
            "com.example.demo.email.api.v2",
            "com.example.demo.notice.api.v2",
            "com.example.demo.parsing.api.v2",
            "com.example.demo.session.api.v2"
    };

    @Bean
    public GroupedOpenApi defaultApi() {
        return GroupedOpenApi.builder()
                .group("default")
                .packagesToExclude(V2_API_PACKAGES)
                .build();
    }

    @Bean
    public GroupedOpenApi v2Api() {
        return GroupedOpenApi.builder()
                .group("v2")
                .packagesToScan(V2_API_PACKAGES)
                .build();
    }
}

