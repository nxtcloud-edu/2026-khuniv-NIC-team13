package com.example.demo.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * DynamoDB 설정 프로퍼티
 * application.yml에서 dynamodb.* 설정을 바인딩
 */
@Data
@ConfigurationProperties(prefix = "dynamodb")
public class DynamoDBProperties {
    
    /**
     * AWS 리전 설정
     */
    private String region = "ap-northeast-2";
    
    /**
     * DynamoDB 엔드포인트 (로컬 개발용)
     */
    private String endpoint;
    
    /**
     * 테이블 이름 설정
     */
    private Tables tables = new Tables();
    
    @Data
    public static class Tables {
        private String notices = "pertineo-notices";
        private String emails = "pertineo-emails";
        private String admins = "pertineo-admins";
        private String whitelist = "pertineo-whitelist";
        private String properties = "pertineo-properties";
        private String locks = "pertineo-locks";
        private String accessCodes = "pertineo-access-codes";
        private String popups = "pertineo-popups";
        private String sessions = "pertineo-sessions";
        private String memberDocuments = "pertineo-member-documents";
    }
}