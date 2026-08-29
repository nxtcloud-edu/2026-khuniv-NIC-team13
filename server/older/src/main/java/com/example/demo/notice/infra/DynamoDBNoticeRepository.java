package com.example.demo.notice.infra;

import com.example.demo.config.DynamoDBProperties;
import com.example.demo.notice.domain.Notice;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Repository;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.DeleteItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemResponse;
import software.amazon.awssdk.services.dynamodb.model.PutItemRequest;
import software.amazon.awssdk.services.dynamodb.model.ScanRequest;
import software.amazon.awssdk.services.dynamodb.model.ScanResponse;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Notice 엔티티용 DynamoDB Repository 구현
 */
@Repository
@RequiredArgsConstructor
@Slf4j
public class DynamoDBNoticeRepository implements NoticeRepository {

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    @Override
    public Notice save(Notice notice) {
        Map<String, AttributeValue> item = new HashMap<>();
        
        // ID가 없으면 생성
        String id = notice.getId() != null ? notice.getId().toString() : generateTimestampId();
        item.put("id", AttributeValue.builder().s(id).build());
        
        if (notice.getTitle() != null) {
            item.put("title", AttributeValue.builder().s(notice.getTitle()).build());
        }
        if (notice.getContent() != null) {
            item.put("content", AttributeValue.builder().s(notice.getContent()).build());
        }
        
        LocalDateTime now = LocalDateTime.now();
        if (notice.getCreatedAt() != null) {
            item.put("createdAt", AttributeValue.builder().s(notice.getCreatedAt().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)).build());
        } else {
            item.put("createdAt", AttributeValue.builder().s(now.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)).build());
        }
        
        item.put("modifiedAt", AttributeValue.builder().s(now.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)).build());

        PutItemRequest putItemRequest = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getNotices())
                .item(item)
                .build();

        try {
            dynamoDbClient.putItem(putItemRequest);
            notice.setId(Long.parseLong(id.split("-")[0])); // 타임스탬프 부분만 Long으로 변환
            return notice;
        } catch (Exception e) {
            log.error("Error saving notice", e);
            throw new RuntimeException("Failed to save notice", e);
        }
    }

    @Override
    public Optional<Notice> findById(Long id) {
        // Long ID로 조회 시 모든 공지사항을 스캔하여 매칭
        List<Notice> allNotices = findAllNotices();
        return allNotices.stream()
                .filter(n -> n.getId() != null && n.getId().equals(id))
                .findFirst();
    }

    @Override
    public Page<Notice> findAll(int page, int size) {
        List<Notice> allNotices = findAllNotices();
        List<Notice> notices = findAllNoticesPaginated(allNotices, page, size);
        
        Pageable pageable = PageRequest.of(page, size);
        return new PageImpl<>(notices, pageable, allNotices.size());
    }

    @Override
    public Optional<Notice> delete(Long id) {
        Optional<Notice> notice = findById(id);
        if (notice.isEmpty()) {
            return Optional.empty();
        }
        
        boolean deleted = deleteNoticeByLongId(id);
        return deleted ? notice : Optional.empty();
    }

    // === Private helper methods ===

    private String generateTimestampId() {
        long timestamp = System.currentTimeMillis();
        String random = UUID.randomUUID().toString().substring(0, 8);
        return timestamp + "-" + random;
    }

    private List<Notice> findAllNotices() {
        List<Notice> notices = new ArrayList<>();
        Map<String, AttributeValue> lastEvaluatedKey = null;

        try {
            do {
                ScanRequest.Builder scanRequestBuilder = ScanRequest.builder()
                        .tableName(dynamoDBProperties.getTables().getNotices());

                if (lastEvaluatedKey != null) {
                    scanRequestBuilder.exclusiveStartKey(lastEvaluatedKey);
                }

                ScanResponse response = dynamoDbClient.scan(scanRequestBuilder.build());
                
                for (Map<String, AttributeValue> item : response.items()) {
                    notices.add(mapToNotice(item));
                }

                lastEvaluatedKey = response.lastEvaluatedKey();
            } while (lastEvaluatedKey != null && !lastEvaluatedKey.isEmpty());

            // createdAt 기준 내림차순 정렬
            notices.sort((a, b) -> {
                if (a.getCreatedAt() == null && b.getCreatedAt() == null) return 0;
                if (a.getCreatedAt() == null) return 1;
                if (b.getCreatedAt() == null) return -1;
                return b.getCreatedAt().compareTo(a.getCreatedAt());
            });

            return notices;
        } catch (Exception e) {
            log.error("Error finding all notices", e);
            throw new RuntimeException("Failed to find all notices", e);
        }
    }

    private List<Notice> findAllNoticesPaginated(List<Notice> allNotices, int page, int size) {
        int start = page * size;
        int end = Math.min(start + size, allNotices.size());
        
        if (start >= allNotices.size()) {
            return new ArrayList<>();
        }
        
        return allNotices.subList(start, end);
    }

    private boolean deleteNoticeByLongId(Long id) {
        // 모든 공지사항을 스캔하여 Long ID와 매칭되는 DynamoDB ID 찾기
        Map<String, AttributeValue> lastEvaluatedKey = null;
        
        try {
            do {
                ScanRequest.Builder scanRequestBuilder = ScanRequest.builder()
                        .tableName(dynamoDBProperties.getTables().getNotices());

                if (lastEvaluatedKey != null) {
                    scanRequestBuilder.exclusiveStartKey(lastEvaluatedKey);
                }

                ScanResponse response = dynamoDbClient.scan(scanRequestBuilder.build());
                
                for (Map<String, AttributeValue> item : response.items()) {
                    Notice notice = mapToNotice(item);
                    if (notice.getId() != null && notice.getId().equals(id)) {
                        // 실제 DynamoDB ID로 삭제
                        String dynamoId = item.get("id").s();
                        return deleteNoticeByDynamoId(dynamoId);
                    }
                }

                lastEvaluatedKey = response.lastEvaluatedKey();
            } while (lastEvaluatedKey != null && !lastEvaluatedKey.isEmpty());
            
            return false;
        } catch (Exception e) {
            log.error("Error deleting notice by long id: {}", id, e);
            return false;
        }
    }

    private boolean deleteNoticeByDynamoId(String id) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("id", AttributeValue.builder().s(id).build());

        DeleteItemRequest deleteItemRequest = DeleteItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getNotices())
                .key(key)
                .build();

        try {
            dynamoDbClient.deleteItem(deleteItemRequest);
            return true;
        } catch (Exception e) {
            log.error("Error deleting notice: {}", id, e);
            return false;
        }
    }

    private Notice mapToNotice(Map<String, AttributeValue> item) {
        Notice notice = new Notice();
        
        if (item.containsKey("id")) {
            String idStr = item.get("id").s();
            try {
                notice.setId(Long.parseLong(idStr.split("-")[0]));
            } catch (Exception e) {
                log.warn("Failed to parse notice id: {}", idStr);
            }
        }
        if (item.containsKey("title")) {
            notice.setTitle(item.get("title").s());
        }
        if (item.containsKey("content")) {
            notice.setContent(item.get("content").s());
        }
        if (item.containsKey("createdAt")) {
            try {
                notice.setCreatedAt(LocalDateTime.parse(item.get("createdAt").s(), DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            } catch (Exception e) {
                log.warn("Failed to parse createdAt: {}", item.get("createdAt").s());
            }
        }
        if (item.containsKey("modifiedAt")) {
            try {
                notice.setModifiedAt(LocalDateTime.parse(item.get("modifiedAt").s(), DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            } catch (Exception e) {
                log.warn("Failed to parse modifiedAt: {}", item.get("modifiedAt").s());
            }
        }
        
        return notice;
    }
}
