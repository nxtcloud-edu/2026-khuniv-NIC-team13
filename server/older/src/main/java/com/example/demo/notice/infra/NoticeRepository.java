package com.example.demo.notice.infra;

import com.example.demo.notice.domain.Notice;
import org.springframework.data.domain.Page;

import java.util.Optional;

public interface NoticeRepository {

    Notice save(Notice notice);

    Optional<Notice> findById(Long id);

    Page<Notice> findAll(int page, int size);

    Optional<Notice> delete(Long id);

}