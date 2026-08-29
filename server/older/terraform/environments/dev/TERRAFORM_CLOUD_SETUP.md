# Terraform Cloud 설정 가이드

## 문제: 모듈 경로를 찾을 수 없음

Terraform Cloud에서 원격 실행(Remote Execution)을 사용할 때 상대 경로 모듈(`../../modules/*`)을 찾을 수 없는 경우가 있습니다.

## 해결 방법

### 방법 1: Execution Mode를 "Local"로 변경 (권장)

1. https://app.terraform.io 접속
2. Organization: `pertino` → Workspace: `pertino-dev` 선택
3. **Settings** → **General Settings**로 이동
4. **Execution Mode** 섹션에서:
   - **Local** 선택
   - **Save settings** 클릭

이렇게 하면 Terraform 명령이 로컬에서 실행되고, 상대 경로가 정상적으로 작동합니다.

### 방법 2: Git 저장소 연결 (VCS-Driven Workflow)

1. Workspace 설정에서 **Version Control** 선택
2. Git 저장소 연결 (GitHub, GitLab 등)
3. Terraform Cloud가 Git에서 코드를 가져오도록 설정

이 경우 상대 경로가 정상적으로 작동합니다.

### 방법 3: 절대 경로 사용 (비권장)

모듈 경로를 절대 경로로 변경할 수 있지만, 이는 이식성을 떨어뜨립니다.

## 현재 권장 설정

**Execution Mode: Local**

이 설정을 사용하면:
- Terraform 명령이 로컬에서 실행됨
- State는 Terraform Cloud에 저장됨
- 상대 경로 모듈이 정상 작동함
- 로컬에서 빠르게 실행 가능

## 확인 방법

Execution Mode를 Local로 변경한 후:

```bash
cd terraform/environments/dev
terraform plan
```

정상적으로 실행되면 성공입니다.

