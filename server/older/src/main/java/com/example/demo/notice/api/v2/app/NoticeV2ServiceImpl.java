package com.example.demo.notice.api.v2.app;

import com.example.demo.notice.api.v2.domain.NoticeV2;
import com.example.demo.notice.api.v2.dto.NoticeV2UpdateRequest;
import com.example.demo.notice.api.v2.infra.NoticeV2Repository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class NoticeV2ServiceImpl implements NoticeV2Service {

    private final NoticeV2Repository noticeV2Repository;

    @Override
    public NoticeV2 create(String title, String content) {
        LocalDateTime now = LocalDateTime.now();
        NoticeV2 notice = new NoticeV2();
        notice.setTitle(title);
        notice.setContent(content);
        notice.setCreatedAt(now);
        notice.setModifiedAt(now);
        noticeV2Repository.save(notice);
        return noticeV2Repository.findById(notice.getId()).orElse(notice);
    }

    @Override
    public Page<NoticeV2> list(int pageIndex, int size) {
        return noticeV2Repository.findAll(pageIndex, size);
    }

    @Override
    public Optional<NoticeV2> get(Long id) {
        return noticeV2Repository.findById(id);
    }

    @Override
    public Optional<NoticeV2> update(Long id, NoticeV2UpdateRequest request) {
        NoticeV2UpdateRequest body = request != null ? request : new NoticeV2UpdateRequest();
        return noticeV2Repository.findById(id).flatMap(existing -> {
            String title = body.getTitle() != null ? body.getTitle() : existing.getTitle();
            String content = body.getContent() != null ? body.getContent() : existing.getContent();
            return noticeV2Repository.update(id, title, content);
        });
    }

    @Override
    public Optional<NoticeV2> delete(Long id) {
        return noticeV2Repository.delete(id);
    }
}
