package com.example.demo.notice.app;

import com.example.demo.notice.domain.Notice;
import org.springframework.data.domain.Page;

import java.util.Optional;

public interface NoticeService {


    Optional<Notice> findNoticeById(Long id);

    Page<Notice> getAllNotice(int page, int size);

}