package com.example.demo.admin.api;

import com.example.demo.notice.infra.NoticeRepository;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletResponse;
import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@Controller
@RequiredArgsConstructor
public class AdminLoginController {
    /*
    컨트롤러마다 CookieValue 있는데 디폴트가 required = true 여서
    로그인 필터 용도로 사용은 안해도 파라미터로 받고있음
     */
    private final NoticeRepository noticeRepository;
    @GetMapping("/admin")
    String getAdminLoginPage(@CookieValue(required = false) String loginStatus,
                             @RequestParam(defaultValue = "0") Integer page, @RequestParam(defaultValue = "10") Integer size, Model model) {

        if (loginStatus == null)
            return "login";
        else {
            model.addAttribute("notices", noticeRepository.findAll(page, size));
            model.addAttribute("today", LocalDate.now());
            return "notices";
        }
    }

    @PostMapping("/admin/login")
    String login(@RequestBody AdminNoticesController.LoginRequest loginRequest,
               HttpServletResponse response, @RequestParam(defaultValue = "0") Integer page, @RequestParam(defaultValue = "10") Integer size, Model model){
        if (!"admin".equals(loginRequest.getUsername()) || !"1234".equals(loginRequest.getPassword())) {
            throw new IllegalStateException("로그인 실패");

        }

        Cookie loginCookie = new Cookie("loginStatus", "success");
        loginCookie.setMaxAge(60 * 10); // 10min
        loginCookie.setPath("/");
        loginCookie.setHttpOnly(false);

        response.addCookie(loginCookie);

        model.addAttribute("notices", noticeRepository.findAll(page, size));
        model.addAttribute("today", LocalDate.now());

        return "notices";
    }

    @Getter
    public static class LoginRequest {
        private String username;
        private String password;
        // getters, setters
    }


}
