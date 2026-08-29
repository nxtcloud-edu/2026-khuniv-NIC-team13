package com.example.demo.admin.api;

import com.example.demo.notice.api.v2.infra.NoticeV2Repository;
import com.example.demo.notice.domain.Notice;
import com.example.demo.notice.infra.NoticeRepository;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Controller;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Optional;

@Controller
@RequiredArgsConstructor
public class AdminNoticesController {

    private final NoticeRepository noticeRepository;
    private final NoticeV2Repository noticeV2Repository;

    @PostMapping("/admin/notices")
    public String handleLoginRequest(@CookieValue String loginStatus, @RequestParam(defaultValue = "0") Integer page, @RequestParam(defaultValue = "10") Integer size, Model model) {

        model.addAttribute("notices", noticeRepository.findAll(page, size));
        model.addAttribute("today", LocalDate.now());
        return "notices";

    }


    @GetMapping("/admin/notices/detail/{id}")
    String noticeDetail(@CookieValue String loginStatus, @PathVariable Long id, Model model){

        Optional<Notice> notice = noticeRepository.findById(id);
        notice.ifPresent(value -> model.addAttribute("notice", value));
        return "notice-detail";
    }

    @GetMapping("/admin/notices/edit/{id}")
    String noticeEdit(@CookieValue String loginStatus, @PathVariable Long id, Model model){

        Optional<Notice> notice = noticeRepository.findById(id);
        notice.ifPresent(value -> model.addAttribute("notice", value));

        return "notice-edit";
    }

    @PostMapping("/admin/notices/edit/{id}")
    @Transactional
    String noticeEditSave(@CookieValue String loginStatus, @RequestParam String content, @RequestParam String title, @PathVariable Long id) {
        noticeV2Repository.update(id, title, content);
        return "redirect:/admin/notices/detail/" + id;
    }

    @PostMapping("/admin/notices/delete/{id}")
    @Transactional
    String deleteNotice(@CookieValue String loginStatus, @PathVariable Long id){


        Optional<Notice> notice = noticeRepository.findById(id);

        noticeRepository.delete(id);


        return "redirect:/admin";
    }

    @GetMapping("/admin/notices/form")
    String noticeForm(@CookieValue String loginStatus){

        return "notice-form";
    }

    @PostMapping("/admin/notices/form")
    @Transactional
    String noticeFormSave(@CookieValue String loginStatus, @RequestParam String content, @RequestParam String title, Model model){
        Notice notice = new Notice();
        notice.setTitle(title);
        notice.setContent(content);
        notice.setModifiedAt(LocalDateTime.now());
        notice.setCreatedAt(LocalDateTime.now());

        noticeRepository.save(notice);
        return "redirect:/admin/notices/detail/" + notice.getId();
    }

    @Getter
    public static class LoginRequest {
        private String username;
        private String password;
    }

    @Getter
    public static class NoticeRequest {
        private String title;
        private String content;
    }
}
