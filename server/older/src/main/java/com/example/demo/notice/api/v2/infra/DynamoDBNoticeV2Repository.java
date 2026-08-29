package com.example.demo.notice.api.v2.infra;

import com.example.demo.notice.api.v2.domain.NoticeV2;
import com.example.demo.config.DynamoDBProperties;
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

@Repository
@RequiredArgsConstructor
@Slf4j
public class DynamoDBNoticeV2Repository implements NoticeV2Repository {

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    /** DynamoDB partition key 문자열 + 매핑된 도메인 (단건 조회·수정·삭제 시 동일 행 보장) */
    private record DynamoNoticeRow(String dynamoId, NoticeV2 notice) {}

    @Override
    public NoticeV2 save(NoticeV2 notice) {
        Map<String, AttributeValue> item = new HashMap<>();

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
            notice.setId(Long.parseLong(id.split("-")[0]));
            return notice;
        } catch (Exception e) {
            log.error("Error saving notice (v2)", e);
            throw new RuntimeException("Failed to save notice", e);
        }
    }

    @Override
    public Optional<NoticeV2> findById(Long id) {
        return findRowByLongId(id).map(DynamoNoticeRow::notice);
    }

    @Override
    public Page<NoticeV2> findAll(int page, int size) {
        List<NoticeV2> allNotices = findAllNotices();
        List<NoticeV2> notices = findAllNoticesPaginated(allNotices, page, size);

        Pageable pageable = PageRequest.of(page, size);
        return new PageImpl<>(notices, pageable, allNotices.size());
    }

    @Override
    public Optional<NoticeV2> update(Long id, String title, String content) {
        Optional<DynamoNoticeRow> rowOpt = findRowByLongId(id);
        if (rowOpt.isEmpty()) {
            return Optional.empty();
        }
        DynamoNoticeRow row = rowOpt.get();
        String dynamoId = row.dynamoId();
        NoticeV2 existing = row.notice();

        LocalDateTime now = LocalDateTime.now();
        LocalDateTime createdAt = existing.getCreatedAt() != null ? existing.getCreatedAt() : now;

        Map<String, AttributeValue> item = new HashMap<>();
        item.put("id", AttributeValue.builder().s(dynamoId).build());
        item.put("title", AttributeValue.builder().s(title != null ? title : "").build());
        item.put("content", AttributeValue.builder().s(content != null ? content : "").build());
        item.put("createdAt", AttributeValue.builder().s(createdAt.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)).build());
        item.put("modifiedAt", AttributeValue.builder().s(now.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)).build());

        PutItemRequest putItemRequest = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getNotices())
                .item(item)
                .build();

        try {
            dynamoDbClient.putItem(putItemRequest);
            // 스캔(findById)은 기본적으로 eventually consistent라 Put 직후 재조회가 비어 나올 수 있음 → 저장 값으로 응답
            NoticeV2 updated = new NoticeV2();
            updated.setId(id);
            updated.setTitle(title != null ? title : "");
            updated.setContent(content != null ? content : "");
            updated.setCreatedAt(createdAt);
            updated.setModifiedAt(now);
            return Optional.of(updated);
        } catch (Exception e) {
            log.error("Error updating notice (v2) by long id: {}", id, e);
            return Optional.empty();
        }
    }

    @Override
    public Optional<NoticeV2> delete(Long id) {
        return findRowByLongId(id).flatMap(row -> {
            if (deleteNoticeByDynamoId(row.dynamoId())) {
                return Optional.of(row.notice());
            }
            return Optional.empty();
        });
    }

    private String generateTimestampId() {
        long timestamp = System.currentTimeMillis();
        String random = UUID.randomUUID().toString().substring(0, 8);
        return timestamp + "-" + random;
    }

    private List<NoticeV2> findAllNotices() {
        List<NoticeV2> notices = new ArrayList<>();
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

            notices.sort((a, b) -> {
                if (a.getCreatedAt() == null && b.getCreatedAt() == null) {
                    return 0;
                }
                if (a.getCreatedAt() == null) {
                    return 1;
                }
                if (b.getCreatedAt() == null) {
                    return -1;
                }
                return b.getCreatedAt().compareTo(a.getCreatedAt());
            });

            return notices;
        } catch (Exception e) {
            log.error("Error finding all notices (v2)", e);
            throw new RuntimeException("Failed to find all notices", e);
        }
    }

    private List<NoticeV2> findAllNoticesPaginated(List<NoticeV2> allNotices, int page, int size) {
        int start = page * size;
        int end = Math.min(start + size, allNotices.size());

        if (start >= allNotices.size()) {
            return new ArrayList<>();
        }

        return allNotices.subList(start, end);
    }

    /**
     * 스캔으로 Long id에 해당하는 행을 찾을 때, DynamoDB 키 문자열(S/N)과 mapToNotice 결과를 같은 item에서 얻어
     * findById와 update/delete가 서로 다른 행을 가리키는 경우를 막습니다.
     */
    private Optional<DynamoNoticeRow> findRowByLongId(Long id) {
        Map<String, AttributeValue> lastEvaluatedKey = null;

        try {
            do {
                ScanRequest.Builder scanRequestBuilder = ScanRequest.builder()
                        .tableName(dynamoDBProperties.getTables().getNotices())
                        .consistentRead(true);

                if (lastEvaluatedKey != null) {
                    scanRequestBuilder.exclusiveStartKey(lastEvaluatedKey);
                }

                ScanResponse response = dynamoDbClient.scan(scanRequestBuilder.build());

                for (Map<String, AttributeValue> item : response.items()) {
                    Optional<String> dynamoIdOpt = extractDynamoKeyString(item.get("id"));
                    if (dynamoIdOpt.isEmpty()) {
                        continue;
                    }
                    String dynamoId = dynamoIdOpt.get();
                    try {
                        Long parsed = Long.parseLong(dynamoId.split("-")[0]);
                        if (parsed.equals(id)) {
                            return Optional.of(new DynamoNoticeRow(dynamoId, mapToNotice(item)));
                        }
                    } catch (Exception ignore) {
                        // ignore
                    }
                }

                lastEvaluatedKey = response.lastEvaluatedKey();
            } while (lastEvaluatedKey != null && !lastEvaluatedKey.isEmpty());

            return Optional.empty();
        } catch (Exception e) {
            log.error("Error finding row (v2) by long id: {}", id, e);
            return Optional.empty();
        }
    }

    private static Optional<String> extractDynamoKeyString(AttributeValue idAttr) {
        if (idAttr == null) {
            return Optional.empty();
        }
        if (idAttr.s() != null && !idAttr.s().isEmpty()) {
            return Optional.of(idAttr.s());
        }
        if (idAttr.n() != null && !idAttr.n().isEmpty()) {
            return Optional.of(idAttr.n());
        }
        return Optional.empty();
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
            log.error("Error deleting notice (v2): {}", id, e);
            return false;
        }
    }

    private NoticeV2 mapToNotice(Map<String, AttributeValue> item) {
        NoticeV2 notice = new NoticeV2();

        extractDynamoKeyString(item.get("id")).ifPresent(idStr -> {
            try {
                notice.setId(Long.parseLong(idStr.split("-")[0]));
            } catch (Exception e) {
                log.warn("Failed to parse notice id (v2): {}", idStr);
            }
        });
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
                log.warn("Failed to parse createdAt (v2): {}", item.get("createdAt").s());
            }
        }
        if (item.containsKey("modifiedAt")) {
            try {
                notice.setModifiedAt(LocalDateTime.parse(item.get("modifiedAt").s(), DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            } catch (Exception e) {
                log.warn("Failed to parse modifiedAt (v2): {}", item.get("modifiedAt").s());
            }
        }

        return notice;
    }
}
