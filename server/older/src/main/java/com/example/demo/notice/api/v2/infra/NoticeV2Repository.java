package com.example.demo.notice.api.v2.infra;

import com.example.demo.notice.api.v2.domain.NoticeV2;
import org.springframework.data.domain.Page;

import java.util.Optional;

public interface NoticeV2Repository {

    NoticeV2 save(NoticeV2 notice);

    Optional<NoticeV2> findById(Long id);

    Page<NoticeV2> findAll(int page, int size);

    Optional<NoticeV2> update(Long id, String title, String content);

    Optional<NoticeV2> delete(Long id);
}
