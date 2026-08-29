package com.example.demo.notice.api.v2.controller;

import com.example.demo.shared.web.v2.V2ApiHeaders;
import com.example.demo.shared.web.v2.response.ErrorCode;
import com.example.demo.shared.web.v2.response.ErrorResponse;
import com.example.demo.shared.web.v2.response.SuccessCode;
import com.example.demo.shared.web.v2.response.SuccessResponse;
import com.example.demo.notice.api.v2.app.NoticeV2Service;
import com.example.demo.notice.api.v2.dto.NoticeV2CreateData;
import com.example.demo.notice.api.v2.dto.NoticeV2CreateRequest;
import com.example.demo.notice.api.v2.dto.NoticeV2DeleteData;
import com.example.demo.notice.api.v2.dto.NoticeV2DetailData;
import com.example.demo.notice.api.v2.dto.NoticeV2ListData;
import com.example.demo.notice.api.v2.domain.NoticeV2;
import com.example.demo.notice.api.v2.dto.NoticeV2ListItemDto;
import com.example.demo.notice.api.v2.dto.NoticeV2PatchData;
import com.example.demo.notice.api.v2.dto.NoticeV2UpdateRequest;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@RestController
@RequestMapping(value = "/api/notice", headers = V2ApiHeaders.MAPPING_CONDITION)
@RequiredArgsConstructor
@Tag(name = "Notice V2", description = "공지 v2 (목록: GET /api/notices, 상세·CRUD: /api/notice)")
public class V2NoticeApiController {

    private static final String AUTHOR = "admin";

    private final NoticeV2Service noticeV2Service;

    @PostMapping
    public ResponseEntity<?> create(@RequestBody NoticeV2CreateRequest request) {
        NoticeV2 created = noticeV2Service.create(request.getTitle(), request.getContent());
        NoticeV2CreateData data = new NoticeV2CreateData(
                created.getId(),
                AUTHOR,
                created.getTitle(),
                created.getContent(),
                created.getCreatedAt(),
                created.getModifiedAt()
        );
        return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, data));
    }

    @GetMapping
    public ResponseEntity<SuccessResponse<NoticeV2ListData>> list(
            @RequestParam Integer page,
            @RequestParam Integer size
    ) {
        int safePage = page != null ? Math.max(1, page) : 1;
        int safeSize = size != null ? Math.max(1, size) : 10;

        Page<NoticeV2> noticePage = noticeV2Service.list(safePage - 1, safeSize);
        NoticeV2ListData data = new NoticeV2ListData(
                toListElements(noticePage),
                noticePage.getTotalElements(),
                safePage
        );
        return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, data));
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> get(@PathVariable Long id) {
        return noticeV2Service.get(id)
                .<ResponseEntity<?>>map(notice -> ResponseEntity.ok(
                        SuccessResponse.of(SuccessCode.SUCCESS, toDetailData(notice))
                ))
                .orElseGet(this::notFound);
    }

    @RequestMapping(value = "/{id}", method = {RequestMethod.PATCH, RequestMethod.PUT})
    public ResponseEntity<?> patch(
            @PathVariable Long id,
            @RequestBody(required = false) NoticeV2UpdateRequest request) {
        return noticeV2Service.update(id, request)
                .<ResponseEntity<?>>map(updated -> ResponseEntity.ok(
                        SuccessResponse.of(SuccessCode.SUCCESS, new NoticeV2PatchData(
                                updated.getId(),
                                updated.getTitle(),
                                updated.getModifiedAt()
                        ))
                ))
                .orElseGet(this::notFound);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> delete(@PathVariable Long id) {
        return noticeV2Service.delete(id)
                .<ResponseEntity<?>>map(notice -> {
                    LocalDateTime deletedAt = LocalDateTime.now();
                    NoticeV2DeleteData data = new NoticeV2DeleteData(
                            notice.getId(),
                            notice.getTitle(),
                            deletedAt
                    );
                    return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, data));
                })
                .orElseGet(this::notFound);
    }

    private ResponseEntity<?> notFound() {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(ErrorResponse.of(ErrorCode.NOTICE_NOT_FOUND));
    }

    private static List<NoticeV2ListItemDto> toListElements(Page<NoticeV2> noticePage) {
        List<NoticeV2ListItemDto> result = new ArrayList<>();
        for (NoticeV2 notice : noticePage) {
            NoticeV2ListItemDto elem = new NoticeV2ListItemDto();
            elem.setId(notice.getId());
            elem.setTitle(notice.getTitle());
            elem.setModifiedAt(notice.getModifiedAt());
            result.add(elem);
        }
        return result;
    }

    private static NoticeV2DetailData toDetailData(NoticeV2 notice) {
        return new NoticeV2DetailData(
                notice.getId(),
                AUTHOR,
                notice.getTitle(),
                notice.getContent(),
                notice.getCreatedAt(),
                notice.getModifiedAt()
        );
    }
}