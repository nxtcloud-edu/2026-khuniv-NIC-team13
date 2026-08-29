package com.example.demo.notice.api.v2.app;

import com.example.demo.notice.api.v2.domain.NoticeV2;
import com.example.demo.notice.api.v2.dto.NoticeV2UpdateRequest;
import org.springframework.data.domain.Page;

import java.util.Optional;

public interface NoticeV2Service {

    NoticeV2 create(String title, String content);

    Page<NoticeV2> list(int pageIndex, int size);

    Optional<NoticeV2> get(Long id);

    Optional<NoticeV2> update(Long id, NoticeV2UpdateRequest request);

    Optional<NoticeV2> delete(Long id);
}
