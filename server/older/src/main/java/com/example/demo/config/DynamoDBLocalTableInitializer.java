package com.example.demo.config;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.*;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 로컬 개발 환경에서 DynamoDB 테이블 자동 생성
 * 
 * local 프로필로 애플리케이션 시작 시 필요한 테이블들을 자동으로 생성합니다.
 * DynamoDB Local이 실행 중이지 않으면 graceful하게 건너뜁니다.
 */
@Configuration
@Profile("local")
@RequiredArgsConstructor
@Slf4j
public class DynamoDBLocalTableInitializer {

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties properties;

    @PostConstruct
    public void initializeTables() {
        try {
            // DynamoDB Local 연결 확인
            if (!isDynamoDBLocalRunning()) {
                log.warn("===========================================");
                log.warn("DynamoDB Local이 실행 중이 아닙니다!");
                log.warn("테이블 자동 생성을 건너뜁니다.");
                log.warn("");
                log.warn("DynamoDB Local 시작 방법:");
                log.warn("  docker-compose up dynamodb-local -d");
                log.warn("===========================================");
                return;
            }

            log.info("DynamoDB Local 테이블 초기화 시작...");

            createAllTables();

            log.info("DynamoDB Local 테이블 초기화 완료");
        } catch (Exception e) {
            log.warn("테이블 초기화 실패: {} - 애플리케이션은 계속 실행됩니다.", e.getMessage());
        }
    }

    /**
     * DynamoDB Local 실행 여부 확인
     */
    private boolean isDynamoDBLocalRunning() {
        try {
            dynamoDbClient.listTables(ListTablesRequest.builder().limit(1).build());
            return true;
        } catch (Exception e) {
            log.debug("DynamoDB Local 연결 실패: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 모든 테이블 생성
     */
    private void createAllTables() {
        log.info("로컬 테이블 생성 시작...");

        createNoticesTable();
        createEmailsTable();
        createAdminsTable();
        createWhitelistTable();
        createPropertiesTable();
        createLocksTable();
        createAccessCodesTable();
        createPopupsTable();
        createSessionsTable();
        createMemberDocumentsTable();

        log.info("로컬 테이블 생성 완료");
    }

    private void createNoticesTable() {
        createTableIfNotExists(
            properties.getTables().getNotices(),
            Arrays.asList(
                AttributeDefinition.builder().attributeName("id").attributeType(ScalarAttributeType.S).build()
            ),
            Arrays.asList(
                KeySchemaElement.builder().attributeName("id").keyType(KeyType.HASH).build()
            )
        );
    }

    private void createEmailsTable() {
        createTableIfNotExists(
            properties.getTables().getEmails(),
            Arrays.asList(
                AttributeDefinition.builder().attributeName("email").attributeType(ScalarAttributeType.S).build()
            ),
            Arrays.asList(
                KeySchemaElement.builder().attributeName("email").keyType(KeyType.HASH).build()
            )
        );
    }

    private void createAdminsTable() {
        createTableIfNotExists(
            properties.getTables().getAdmins(),
            Arrays.asList(
                AttributeDefinition.builder().attributeName("email").attributeType(ScalarAttributeType.S).build()
            ),
            Arrays.asList(
                KeySchemaElement.builder().attributeName("email").keyType(KeyType.HASH).build()
            )
        );
    }

    private void createWhitelistTable() {
        createTableIfNotExists(
            properties.getTables().getWhitelist(),
            Arrays.asList(
                AttributeDefinition.builder().attributeName("email").attributeType(ScalarAttributeType.S).build()
            ),
            Arrays.asList(
                KeySchemaElement.builder().attributeName("email").keyType(KeyType.HASH).build()
            )
        );
    }

    private void createPropertiesTable() {
        createTableIfNotExists(
            properties.getTables().getProperties(),
            Arrays.asList(
                AttributeDefinition.builder().attributeName("id").attributeType(ScalarAttributeType.S).build()
            ),
            Arrays.asList(
                KeySchemaElement.builder().attributeName("id").keyType(KeyType.HASH).build()
            )
        );
    }

    private void createLocksTable() {
        createTableIfNotExists(
            properties.getTables().getLocks(),
            Arrays.asList(
                AttributeDefinition.builder().attributeName("lock_key").attributeType(ScalarAttributeType.S).build()
            ),
            Arrays.asList(
                KeySchemaElement.builder().attributeName("lock_key").keyType(KeyType.HASH).build()
            )
        );
    }

    private void createAccessCodesTable() {
        createTableIfNotExists(
            properties.getTables().getAccessCodes(),
            Arrays.asList(
                AttributeDefinition.builder().attributeName("access_code_key").attributeType(ScalarAttributeType.S).build()
            ),
            Arrays.asList(
                KeySchemaElement.builder().attributeName("access_code_key").keyType(KeyType.HASH).build()
            )
        );
    }

    private void createPopupsTable() {
        createTableIfNotExists(
            properties.getTables().getPopups(),
            Arrays.asList(
                AttributeDefinition.builder().attributeName("id").attributeType(ScalarAttributeType.S).build()
            ),
            Arrays.asList(
                KeySchemaElement.builder().attributeName("id").keyType(KeyType.HASH).build()
            )
        );
    }

    private void createSessionsTable() {
        String tableName = properties.getTables().getSessions();
        try {
            dynamoDbClient.describeTable(DescribeTableRequest.builder().tableName(tableName).build());
            log.debug("테이블 이미 존재: {}", tableName);
        } catch (ResourceNotFoundException e) {
            try {
                CreateTableRequest createTableRequest = CreateTableRequest.builder()
                        .tableName(tableName)
                        .attributeDefinitions(
                                AttributeDefinition.builder().attributeName("session_id").attributeType(ScalarAttributeType.S).build(),
                                AttributeDefinition.builder().attributeName("email").attributeType(ScalarAttributeType.S).build()
                        )
                        .keySchema(
                                KeySchemaElement.builder().attributeName("session_id").keyType(KeyType.HASH).build()
                        )
                        .globalSecondaryIndexes(
                                GlobalSecondaryIndex.builder()
                                        .indexName("email-index")
                                        .keySchema(
                                                KeySchemaElement.builder().attributeName("email").keyType(KeyType.HASH).build()
                                        )
                                        .projection(Projection.builder().projectionType(ProjectionType.ALL).build())
                                        .build()
                        )
                        .billingMode(BillingMode.PAY_PER_REQUEST)
                        .build();

                dynamoDbClient.createTable(createTableRequest);
                log.info("테이블 생성됨: {} (GSI email-index)", tableName);
                waitForTableToBeActive(tableName);
            } catch (Exception ex) {
                log.error("테이블 생성 실패: {} - {}", tableName, ex.getMessage());
            }
        } catch (Exception e) {
            log.warn("테이블 상태 확인 실패: {} - {}", tableName, e.getMessage());
        }
    }

    private void createMemberDocumentsTable() {
        createTableIfNotExists(
            properties.getTables().getMemberDocuments(),
            Arrays.asList(
                AttributeDefinition.builder().attributeName("pk").attributeType(ScalarAttributeType.S).build(),
                AttributeDefinition.builder().attributeName("sk").attributeType(ScalarAttributeType.S).build()
            ),
            Arrays.asList(
                KeySchemaElement.builder().attributeName("pk").keyType(KeyType.HASH).build(),
                KeySchemaElement.builder().attributeName("sk").keyType(KeyType.RANGE).build()
            )
        );
    }

    private void createTableIfNotExists(String tableName, List<AttributeDefinition> attributes, List<KeySchemaElement> keySchema) {
        try {
            // 테이블 존재 여부 확인
            dynamoDbClient.describeTable(DescribeTableRequest.builder().tableName(tableName).build());
            log.debug("테이블 이미 존재: {}", tableName);
        } catch (ResourceNotFoundException e) {
            // 테이블이 없으면 생성
            try {
                CreateTableRequest createTableRequest = CreateTableRequest.builder()
                        .tableName(tableName)
                        .attributeDefinitions(attributes)
                        .keySchema(keySchema)
                        .billingMode(BillingMode.PAY_PER_REQUEST)
                        .build();

                dynamoDbClient.createTable(createTableRequest);
                log.info("테이블 생성됨: {}", tableName);

                // 테이블 생성 완료 대기
                waitForTableToBeActive(tableName);
            } catch (Exception ex) {
                log.error("테이블 생성 실패: {} - {}", tableName, ex.getMessage());
            }
        } catch (Exception e) {
            log.warn("테이블 상태 확인 실패: {} - {}", tableName, e.getMessage());
        }
    }

    /**
     * 테이블이 ACTIVE 상태가 될 때까지 대기
     */
    private void waitForTableToBeActive(String tableName) {
        int maxRetries = 30;
        int retryCount = 0;

        while (retryCount < maxRetries) {
            try {
                DescribeTableResponse response = dynamoDbClient.describeTable(
                    DescribeTableRequest.builder().tableName(tableName).build()
                );

                if (response.table().tableStatus() == TableStatus.ACTIVE) {
                    log.debug("테이블 활성화 완료: {}", tableName);
                    return;
                }

                Thread.sleep(1000);
                retryCount++;
            } catch (Exception e) {
                log.warn("테이블 상태 확인 중 오류: {} - {}", tableName, e.getMessage());
                break;
            }
        }

        log.warn("테이블 활성화 대기 시간 초과: {}", tableName);
    }

    // ========== 테스트 지원 메서드 (테스트에서 사용) ==========

    /**
     * DynamoDB Local이 실행 중인지 확인 (테스트에서 사용)
     */
    public boolean isDynamoDBAvailable() {
        return isDynamoDBLocalRunning();
    }

    /**
     * 모든 테이블의 데이터 정리 (테스트 격리용)
     */
    public void cleanupAllTableData() {
        if (!isDynamoDBLocalRunning()) {
            return;
        }
        
        log.debug("테스트 데이터 정리 시작...");
        
        clearTableData(properties.getTables().getNotices(), "id");
        clearTableData(properties.getTables().getEmails(), "email");
        clearTableData(properties.getTables().getAdmins(), "email");
        clearTableData(properties.getTables().getWhitelist(), "email");
        clearTableData(properties.getTables().getProperties(), "id");
        clearTableData(properties.getTables().getLocks(), "lock_key");
        clearTableData(properties.getTables().getAccessCodes(), "access_code_key");
        clearTableData(properties.getTables().getPopups(), "id");
        clearTableData(properties.getTables().getSessions(), "session_id");
        clearCompositeKeyTableData(properties.getTables().getMemberDocuments(), "pk", "sk");
        
        log.debug("테스트 데이터 정리 완료");
    }

    private void clearCompositeKeyTableData(String tableName, String hashKeyAttribute, String rangeKeyAttribute) {
        try {
            ScanRequest scanRequest = ScanRequest.builder()
                    .tableName(tableName)
                    .build();

            ScanResponse scanResponse = dynamoDbClient.scan(scanRequest);

            for (var item : scanResponse.items()) {
                if (item.containsKey(hashKeyAttribute) && item.containsKey(rangeKeyAttribute)) {
                    Map<String, AttributeValue> key = new HashMap<>();
                    key.put(hashKeyAttribute, item.get(hashKeyAttribute));
                    key.put(rangeKeyAttribute, item.get(rangeKeyAttribute));

                    DeleteItemRequest deleteRequest = DeleteItemRequest.builder()
                            .tableName(tableName)
                            .key(key)
                            .build();
                    dynamoDbClient.deleteItem(deleteRequest);
                }
            }

            log.debug("복합키 테이블 데이터 정리 완료: {}", tableName);
        } catch (Exception e) {
            log.debug("복합키 테이블 데이터 정리 실패 (테이블이 없을 수 있음): {} - {}", tableName, e.getMessage());
        }
    }

    /**
     * 특정 테이블의 모든 데이터 삭제
     */
    private void clearTableData(String tableName, String keyAttribute) {
        try {
            ScanRequest scanRequest = ScanRequest.builder()
                    .tableName(tableName)
                    .build();
            
            ScanResponse scanResponse = dynamoDbClient.scan(scanRequest);
            
            for (var item : scanResponse.items()) {
                if (item.containsKey(keyAttribute)) {
                    Map<String, AttributeValue> key = new HashMap<>();
                    key.put(keyAttribute, item.get(keyAttribute));
                    
                    DeleteItemRequest deleteRequest = DeleteItemRequest.builder()
                            .tableName(tableName)
                            .key(key)
                            .build();
                    dynamoDbClient.deleteItem(deleteRequest);
                }
            }
            
            log.debug("테이블 데이터 정리 완료: {}", tableName);
        } catch (Exception e) {
            log.debug("테이블 데이터 정리 실패 (테이블이 없을 수 있음): {} - {}", tableName, e.getMessage());
        }
    }
}

