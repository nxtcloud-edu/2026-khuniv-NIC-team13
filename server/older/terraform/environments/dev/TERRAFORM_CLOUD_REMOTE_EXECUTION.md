# Terraform Cloud 원격 실행 설정 가이드

## 개요

Terraform Cloud에서 원격 실행(Remote Execution)을 사용하려면 **VCS-Driven Workflow**를 설정해야 합니다. 이렇게 하면 Terraform Cloud가 Git 저장소에서 직접 코드를 가져와서 실행합니다.

## 현재 문제

- **CLI-Driven Workflow**에서는 로컬 파일 시스템의 상대 경로(`../../modules/*`)를 찾을 수 없음
- 원격 실행 시 Terraform Cloud가 로컬 파일을 업로드하지만 상대 경로가 제대로 해석되지 않음

## 해결 방법: VCS-Driven Workflow 설정

### 1. Git 저장소에 코드 푸시

먼저 모든 Terraform 코드를 Git 저장소에 커밋하고 푸시해야 합니다:

```bash
# 현재 브랜치 확인
git branch

# 변경사항 커밋
git add .
git commit -m "feat: Terraform 모듈 및 환경 설정 완료"

# 원격 저장소에 푸시
git push origin <branch-name>
```

### 2. Terraform Cloud에서 VCS 연결

1. **Terraform Cloud 접속**: https://app.terraform.io
2. **Organization 선택**: `pertino`
3. **Workspace 선택**: `pertino-dev` (또는 `pertino-prod`)

### 3. Version Control 설정

1. Workspace 페이지에서 **Settings** → **Version Control** 클릭
2. **Connect a VCS provider** 클릭
3. VCS Provider 선택 (GitHub, GitLab, Bitbucket 등)

#### GitHub 연결 방법

**"GitHub App (Installed)" 옵션이 선택되지 않는 경우:**

이 옵션은 **이미 Organization에 GitHub App이 설치되어 있어야만** 선택할 수 있습니다. 

**해결 방법 1: GitHub.com (Custom) 사용 (권장)**

1. GitHub 버튼 클릭
2. **"GitHub.com (Custom)"** 선택
3. OAuth 인증 진행
4. 저장소 선택 및 연결

이 방법은 Organization에 GitHub App 설치가 필요하지 않고, 개인 또는 Organization 레벨 OAuth 토큰을 사용합니다.

**해결 방법 2: Organization에 GitHub App 설치 (Team/Enterprise용)**

1. Terraform Cloud에서 **Organization Settings** → **VCS Providers** 이동
2. **Connect a VCS provider** 클릭
3. **GitHub** 선택
4. GitHub App 설치 프로세스 진행:
   - GitHub에서 Terraform Cloud App 설치
   - Organization 또는 개인 계정에 설치
   - 필요한 저장소 접근 권한 부여
5. 설치 완료 후 Workspace로 돌아가서 **"GitHub App (Installed)"** 선택 가능

**참고:**
- 개인 프로젝트나 작은 팀: **"GitHub.com (Custom)"** 방식 권장 (간단함)
- 대규모 팀/엔터프라이즈: **GitHub App** 방식 권장 (세밀한 권한 관리)

#### 연결 완료

4. OAuth 인증 완료 (또는 GitHub App 설치 완료)
5. 저장소 선택 및 연결

### 4. Workspace 설정

VCS 연결 후 다음 설정을 구성합니다:

#### Working Directory 설정

- **Working Directory**: `terraform/environments/dev` (또는 `terraform/environments/prod`)

이렇게 하면 Terraform Cloud가 해당 디렉토리를 루트로 인식하고, 상대 경로 `../../modules/*`가 정상 작동합니다.

#### Auto Queue Runs 설정

- **Auto queue runs**: 선택 (PR 머지 시 자동 실행)
- **Trigger patterns**: `terraform/**/*.tf` (Terraform 파일 변경 시만 실행)

### 5. Execution Mode 확인

1. **Settings** → **General Settings**
2. **Execution Mode** 확인:
   - **Remote** 선택 (원격 실행)
   - 또는 **Agent** 선택 (자체 Agent 사용)

### 6. Variables 설정

**Variables** 탭에서 필요한 변수 설정:

| Key | Value | Type | Sensitive |
|-----|-------|------|-----------|
| `aws_region` | `ap-northeast-2` | `terraform` | ❌ |
| `project_name` | `pertino` | `terraform` | ❌ |
| `environment` | `dev` | `terraform` | ❌ |
| `domain_name` | (비워두거나 도메인) | `terraform` | ❌ |
| `enable_nat_gateway` | `true` | `terraform` | ❌ |
| `enable_vpc_endpoints` | `true` | `terraform` | ❌ |
| `AWS_ACCESS_KEY_ID` | (AWS Access Key) | `env` | ✅ |
| `AWS_SECRET_ACCESS_KEY` | (AWS Secret Key) | `env` | ✅ |

### 7. AWS 자격 증명 설정

#### 방법 1: 환경 변수 (간단)

**Variables** 탭에서:
- `AWS_ACCESS_KEY_ID` (Type: `env`, Sensitive: ✅)
- `AWS_SECRET_ACCESS_KEY` (Type: `env`, Sensitive: ✅)

#### 방법 2: AWS IAM Role (권장, 프로덕션)

1. **Settings** → **Cloud Credentials**
2. **AWS Dynamic Credentials** 선택
3. IAM Role ARN 입력
4. Terraform Cloud가 자동으로 임시 자격 증명 생성

## 디렉토리 구조 확인

VCS-Driven Workflow를 사용할 때는 다음 구조가 중요합니다:

```
repository-root/
├── terraform/
│   ├── modules/
│   │   ├── vpc/
│   │   ├── ecr/
│   │   └── ...
│   └── environments/
│       ├── dev/
│       │   ├── main.tf          # ../../modules/* 참조
│       │   ├── backend.tf
│       │   └── providers.tf
│       └── prod/
│           └── ...
```

**Working Directory**를 `terraform/environments/dev`로 설정하면:
- Terraform Cloud는 이 디렉토리를 루트로 인식
- `../../modules/*` 경로가 정상 작동

## 실행 방법

### 자동 실행 (권장)

1. Git에 코드 푸시
2. PR 생성 및 머지
3. Terraform Cloud가 자동으로 Plan 실행
4. UI에서 Apply 승인

### 수동 실행

1. Terraform Cloud Workspace 페이지에서 **Actions** → **Start new plan**
2. Plan 확인 후 **Confirm & Apply** 클릭

## 주의사항

### 1. Backend 설정

`backend.tf` 파일의 `cloud` 블록은 VCS-Driven Workflow에서도 필요합니다:

```hcl
terraform {
  cloud {
    organization = "pertino"
    workspaces {
      name = "pertino-dev"
    }
  }
}
```

### 2. 모듈 경로

VCS-Driven Workflow에서는:
- ✅ `../../modules/*` (상대 경로) - 정상 작동
- ✅ `git::https://github.com/...` (Git URL) - 가능
- ✅ `registry.terraform.io/...` (Terraform Registry) - 가능

### 3. State 관리

- State는 Terraform Cloud에 자동 저장
- 여러 Workspace 간 State 공유 가능
- State Lock 자동 관리

## 문제 해결

### 모듈을 찾을 수 없는 경우

1. **Working Directory 확인**: `terraform/environments/dev`로 설정되어 있는지 확인
2. **Git 저장소 확인**: 모든 파일이 커밋되어 있는지 확인
3. **경로 확인**: `main.tf`에서 `source = "../../modules/vpc"` 형식 확인

### 자격 증명 오류

1. **환경 변수 확인**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` 설정 확인
2. **IAM Role 확인**: Dynamic Credentials 사용 시 IAM Role 권한 확인
3. **리전 확인**: `aws_region` 변수가 올바르게 설정되어 있는지 확인

## 참고

- [Terraform Cloud VCS-Driven Workflow 문서](https://developer.hashicorp.com/terraform/cloud-docs/run/ui)
- [Terraform Cloud Workspace 설정](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/settings)

