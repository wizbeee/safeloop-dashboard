# 점검 환원 데이터 (시연용)

이 폴더는 대시보드가 자동 합산하는 **공공 환원 CSV 보관 위치**입니다.

- 활성 환원: `opendata_*.csv`
- 메타 사이드카: `opendata_*.csv.meta.json`
- 롤백된 환원: `_rolled_back/` 하위 (대시보드는 무시)

실 운영에서는 점검 프로그램(`wizbeee/safeloop`)이 동일 위치에 환원 파일을 저장합니다.
Streamlit Cloud 배포 환경에서는 이 저장소 내부 폴더가 fallback 으로 사용됩니다.

스키마 정의: [`docs/opendata_schema.md`](../../docs/opendata_schema.md)
