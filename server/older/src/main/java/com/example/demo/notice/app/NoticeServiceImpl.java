package com.example.demo.notice.app;

import com.example.demo.notice.domain.Notice;
import com.example.demo.notice.infra.DynamoDBNoticeRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
@RequiredArgsConstructor
public class NoticeServiceImpl implements NoticeService{

    private final DynamoDBNoticeRepository noticeRepository;

    @Override
    public Optional<Notice> findNoticeById(Long id) {
        return noticeRepository.findById(id);
    }

    @Override
    public Page<Notice> getAllNotice(int page, int size) {
        return noticeRepository.findAll(page, size);
    }

}