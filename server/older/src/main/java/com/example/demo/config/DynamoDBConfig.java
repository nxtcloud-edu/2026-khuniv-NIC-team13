package com.example.demo.config;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;

import java.net.URI;

/**
 * DynamoDB 클라이언트 설정
 * 프로필 기반으로 로컬/AWS 환경을 구분하여 설정
 */
@Configuration
@EnableConfigurationProperties(DynamoDBProperties.class)
@RequiredArgsConstructor
@Slf4j
public class DynamoDBConfig {

    private final DynamoDBProperties dynamoDBProperties;

    /**
     * AWS DynamoDB 클라이언트 (프로덕션/개발 환경)
     */
    @Bean
    @Profile("!local")
    public DynamoDbClient dynamoDbClient() {
        log.info("DynamoDB 설정: AWS DynamoDB 사용 (Region: {})", dynamoDBProperties.getRegion());
        logTableConfiguration();
        
        return DynamoDbClient.builder()
                .region(Region.of(dynamoDBProperties.getRegion()))
                .credentialsProvider(DefaultCredentialsProvider.create())
                .build();
    }

    /**
     * 로컬 DynamoDB 클라이언트 (로컬 개발 환경)
     */
    @Bean
    @Profile("local")
    public DynamoDbClient localDynamoDbClient() {
        String endpoint = dynamoDBProperties.getEndpoint() != null 
            ? dynamoDBProperties.getEndpoint() 
            : "http://localhost:8000";
            
        log.info("DynamoDB 설정: 로컬 DynamoDB 사용 - Endpoint: {}", endpoint);
        logTableConfiguration();
        
        return DynamoDbClient.builder()
                .endpointOverride(URI.create(endpoint))
                .region(Region.US_EAST_1) // 로컬에서는 임의 리전 사용
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create("dummy", "dummy")))
                .build();
    }

    private void logTableConfiguration() {
        DynamoDBProperties.Tables tables = dynamoDBProperties.getTables();
        log.info("DynamoDB 테이블 설정 - Notices: {}, Emails: {}, Admins: {}, Whitelist: {}, Properties: {}, Locks: {}, AccessCodes: {}, Popups: {}, Sessions: {}, MemberDocuments: {}",
                tables.getNotices(), tables.getEmails(), tables.getAdmins(), 
                tables.getWhitelist(), tables.getProperties(), tables.getLocks(),
                tables.getAccessCodes(), tables.getPopups(), tables.getSessions(), tables.getMemberDocuments());
    }
}

