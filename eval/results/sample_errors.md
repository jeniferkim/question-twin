# 샘플 오류 사례

`python -m eval.evaluate`로 생성. 질문 하나씩 넣었을 때 1등으로 나온 질문이 같은 묶음이 아닌 경우

- 같은 상담 코드, 다른 요청: 주제는 같지만 필요한 답이 다른 질문을 1등으로 고름
- 다른 상담 코드: 표현만 겹치는 다른 주제의 질문을 1등으로 고름

### MiniLM: 1등이 틀린 질문 24개

| 유형 | 개수 |
| --- | ---: |
| 같은 상담 코드, 다른 요청 | 10 |
| 다른 상담 코드 | 14 |

| 질문 | 1등으로 나온 질문 | 유형 |
| --- | --- | --- |
| 요금제 바꾸고 싶어요 (G01, PLAN_CHANGE) | 요금 납부일을 바꾸고 싶어요 (G02, PAYMENT_METHOD) | 다른 상담 코드 |
| 요금 납부일을 바꾸고 싶어요 (G02, PAYMENT_METHOD) | 요금제 바꾸고 싶어요 (G01, PLAN_CHANGE) | 다른 상담 코드 |
| 매달 요금 빠져나가는 날짜를 25일로 변경할 수 있나요? (G02, PAYMENT_METHOD) | 미납된 요금 즉시 납부할 수 있나요? (G06, BILL_PAYMENT) | 다른 상담 코드 |
| 자동이체 계좌를 다른 은행으로 바꾸고 싶어요 (G03, PAYMENT_METHOD) | 요금제 바꾸고 싶어요 (G01, PLAN_CHANGE) | 다른 상담 코드 |
| 요금 내는 카드를 변경하려면 어떻게 하나요? (G03, PAYMENT_METHOD) | 다른 요금제로 변경할 수 있나요? (G01, PLAN_CHANGE) | 다른 상담 코드 |
| 이번 달 요금이 얼마 나왔는지 알고 싶어요 (G04, BILL_INQUIRY) | 어제 낸 요금이 납부 처리됐는지 확인하고 싶어요 (G07, BILL_PAYMENT) | 다른 상담 코드 |
| 이번 달 청구 금액 확인해 주세요 (G04, BILL_INQUIRY) | 폰 분실 신고하고 정지해 주세요 (G14, SUSPEND_LOST) | 다른 상담 코드 |
| 이번 달 요금이 평소보다 많이 나왔어요 (G05, BILL_INQUIRY) | 이번 달 요금이 얼마 나왔는지 알고 싶어요 (G04, BILL_INQUIRY) | 같은 상담 코드, 다른 요청 |
| 요금이 왜 이렇게 많이 청구됐나요? (G05, BILL_INQUIRY) | 요금 냈는데 정상적으로 납부됐나요? (G07, BILL_PAYMENT) | 다른 상담 코드 |
| 밀린 요금을 지금 바로 내고 싶어요 (G06, BILL_PAYMENT) | 이번 달 청구 금액 확인해 주세요 (G04, BILL_INQUIRY) | 다른 상담 코드 |
| 미납된 요금 즉시 납부할 수 있나요? (G06, BILL_PAYMENT) | 요금 냈는데 정상적으로 납부됐나요? (G07, BILL_PAYMENT) | 같은 상담 코드, 다른 요청 |
| 어제 낸 요금이 납부 처리됐는지 확인하고 싶어요 (G07, BILL_PAYMENT) | 밀린 요금을 지금 바로 내고 싶어요 (G06, BILL_PAYMENT) | 같은 상담 코드, 다른 요청 |
| 요금 냈는데 정상적으로 납부됐나요? (G07, BILL_PAYMENT) | 미납된 요금 즉시 납부할 수 있나요? (G06, BILL_PAYMENT) | 같은 상담 코드, 다른 요청 |
| 선택약정 할인 받으려면 어떻게 신청해요? (G08, CONTRACT_DISCOUNT) | 할인 약정 만료일 확인해 주세요 (G09, CONTRACT_DISCOUNT) | 같은 상담 코드, 다른 요청 |
| 25% 요금 할인 약정에 가입하고 싶어요 (G08, CONTRACT_DISCOUNT) | 할인 약정 만료일 확인해 주세요 (G09, CONTRACT_DISCOUNT) | 같은 상담 코드, 다른 요청 |
| 선택약정이 언제 끝나는지 알고 싶어요 (G09, CONTRACT_DISCOUNT) | 이번 달 청구 금액 확인해 주세요 (G04, BILL_INQUIRY) | 다른 상담 코드 |
| 할인 약정 만료일 확인해 주세요 (G09, CONTRACT_DISCOUNT) | 25% 요금 할인 약정에 가입하고 싶어요 (G08, CONTRACT_DISCOUNT) | 같은 상담 코드, 다른 요청 |
| 가입된 부가서비스를 해지하고 싶어요 (G10, ADDON_SERVICE) | 폰 분실 신고하고 정지해 주세요 (G14, SUSPEND_LOST) | 다른 상담 코드 |
| 제가 어떤 부가서비스에 가입되어 있는지 알고 싶어요 (G11, ADDON_SERVICE) | 가입된 부가서비스를 해지하고 싶어요 (G10, ADDON_SERVICE) | 같은 상담 코드, 다른 요청 |
| 휴대폰 소액결제를 막고 싶어요 (G12, MICRO_PAYMENT) | 휴대폰 소액결제 한도를 올리고 싶어요 (G13, MICRO_PAYMENT) | 같은 상담 코드, 다른 요청 |
| 소액결제 차단 신청할 수 있나요? (G12, MICRO_PAYMENT) | 선택약정 할인 받으려면 어떻게 신청해요? (G08, CONTRACT_DISCOUNT) | 다른 상담 코드 |
| 휴대폰 소액결제 한도를 올리고 싶어요 (G13, MICRO_PAYMENT) | 폰 분실 신고하고 정지해 주세요 (G14, SUSPEND_LOST) | 다른 상담 코드 |
| 소액결제 한도 늘릴 수 있나요? (G13, MICRO_PAYMENT) | 소액결제 차단 신청할 수 있나요? (G12, MICRO_PAYMENT) | 같은 상담 코드, 다른 요청 |
| 폰 분실 신고하고 정지해 주세요 (G14, SUSPEND_LOST) | 가입된 부가서비스를 해지하고 싶어요 (G10, ADDON_SERVICE) | 다른 상담 코드 |

### TF-IDF: 1등이 틀린 질문 27개

| 유형 | 개수 |
| --- | ---: |
| 같은 상담 코드, 다른 요청 | 12 |
| 다른 상담 코드 | 15 |

| 질문 | 1등으로 나온 질문 | 유형 |
| --- | --- | --- |
| 요금제 바꾸고 싶어요 (G01, PLAN_CHANGE) | 요금 납부일을 바꾸고 싶어요 (G02, PAYMENT_METHOD) | 다른 상담 코드 |
| 다른 요금제로 변경할 수 있나요? (G01, PLAN_CHANGE) | 매달 요금 빠져나가는 날짜를 25일로 변경할 수 있나요? (G02, PAYMENT_METHOD) | 다른 상담 코드 |
| 지금 쓰는 요금제를 더 싼 걸로 바꾸려면 어떻게 해요? (G01, PLAN_CHANGE) | 선택약정 할인 받으려면 어떻게 신청해요? (G08, CONTRACT_DISCOUNT) | 다른 상담 코드 |
| 요금 납부일을 바꾸고 싶어요 (G02, PAYMENT_METHOD) | 요금제 바꾸고 싶어요 (G01, PLAN_CHANGE) | 다른 상담 코드 |
| 매달 요금 빠져나가는 날짜를 25일로 변경할 수 있나요? (G02, PAYMENT_METHOD) | 다른 요금제로 변경할 수 있나요? (G01, PLAN_CHANGE) | 다른 상담 코드 |
| 자동이체 계좌를 다른 은행으로 바꾸고 싶어요 (G03, PAYMENT_METHOD) | 요금제 바꾸고 싶어요 (G01, PLAN_CHANGE) | 다른 상담 코드 |
| 요금 내는 카드를 변경하려면 어떻게 하나요? (G03, PAYMENT_METHOD) | 지금 쓰는 요금제를 더 싼 걸로 바꾸려면 어떻게 해요? (G01, PLAN_CHANGE) | 다른 상담 코드 |
| 이번 달 요금이 얼마 나왔는지 알고 싶어요 (G04, BILL_INQUIRY) | 이번 달 요금이 평소보다 많이 나왔어요 (G05, BILL_INQUIRY) | 같은 상담 코드, 다른 요청 |
| 이번 달 청구 금액 확인해 주세요 (G04, BILL_INQUIRY) | 할인 약정 만료일 확인해 주세요 (G09, CONTRACT_DISCOUNT) | 다른 상담 코드 |
| 이번 달 요금이 평소보다 많이 나왔어요 (G05, BILL_INQUIRY) | 이번 달 요금이 얼마 나왔는지 알고 싶어요 (G04, BILL_INQUIRY) | 같은 상담 코드, 다른 요청 |
| 밀린 요금을 지금 바로 내고 싶어요 (G06, BILL_PAYMENT) | 요금 납부일을 바꾸고 싶어요 (G02, PAYMENT_METHOD) | 다른 상담 코드 |
| 미납된 요금 즉시 납부할 수 있나요? (G06, BILL_PAYMENT) | 다른 요금제로 변경할 수 있나요? (G01, PLAN_CHANGE) | 다른 상담 코드 |
| 어제 낸 요금이 납부 처리됐는지 확인하고 싶어요 (G07, BILL_PAYMENT) | 이번 달 요금이 얼마 나왔는지 알고 싶어요 (G04, BILL_INQUIRY) | 다른 상담 코드 |
| 요금 냈는데 정상적으로 납부됐나요? (G07, BILL_PAYMENT) | 미납된 요금 즉시 납부할 수 있나요? (G06, BILL_PAYMENT) | 같은 상담 코드, 다른 요청 |
| 선택약정 할인 받으려면 어떻게 신청해요? (G08, CONTRACT_DISCOUNT) | 지금 쓰는 요금제를 더 싼 걸로 바꾸려면 어떻게 해요? (G01, PLAN_CHANGE) | 다른 상담 코드 |
| 25% 요금 할인 약정에 가입하고 싶어요 (G08, CONTRACT_DISCOUNT) | 할인 약정 만료일 확인해 주세요 (G09, CONTRACT_DISCOUNT) | 같은 상담 코드, 다른 요청 |
| 선택약정이 언제 끝나는지 알고 싶어요 (G09, CONTRACT_DISCOUNT) | 이번 달 요금이 얼마 나왔는지 알고 싶어요 (G04, BILL_INQUIRY) | 다른 상담 코드 |
| 할인 약정 만료일 확인해 주세요 (G09, CONTRACT_DISCOUNT) | 이번 달 청구 금액 확인해 주세요 (G04, BILL_INQUIRY) | 다른 상담 코드 |
| 가입된 부가서비스를 해지하고 싶어요 (G10, ADDON_SERVICE) | 제가 어떤 부가서비스에 가입되어 있는지 알고 싶어요 (G11, ADDON_SERVICE) | 같은 상담 코드, 다른 요청 |
| 쓰지 않는 유료 부가서비스 끊어 주세요 (G10, ADDON_SERVICE) | 이용 중인 부가서비스 목록 보여 주세요 (G11, ADDON_SERVICE) | 같은 상담 코드, 다른 요청 |
| 제가 어떤 부가서비스에 가입되어 있는지 알고 싶어요 (G11, ADDON_SERVICE) | 가입된 부가서비스를 해지하고 싶어요 (G10, ADDON_SERVICE) | 같은 상담 코드, 다른 요청 |
| 이용 중인 부가서비스 목록 보여 주세요 (G11, ADDON_SERVICE) | 쓰지 않는 유료 부가서비스 끊어 주세요 (G10, ADDON_SERVICE) | 같은 상담 코드, 다른 요청 |
| 휴대폰 소액결제를 막고 싶어요 (G12, MICRO_PAYMENT) | 휴대폰 소액결제 한도를 올리고 싶어요 (G13, MICRO_PAYMENT) | 같은 상담 코드, 다른 요청 |
| 소액결제 차단 신청할 수 있나요? (G12, MICRO_PAYMENT) | 소액결제 한도 늘릴 수 있나요? (G13, MICRO_PAYMENT) | 같은 상담 코드, 다른 요청 |
| 휴대폰 소액결제 한도를 올리고 싶어요 (G13, MICRO_PAYMENT) | 휴대폰 소액결제를 막고 싶어요 (G12, MICRO_PAYMENT) | 같은 상담 코드, 다른 요청 |
| 소액결제 한도 늘릴 수 있나요? (G13, MICRO_PAYMENT) | 소액결제 차단 신청할 수 있나요? (G12, MICRO_PAYMENT) | 같은 상담 코드, 다른 요청 |
| 폰 분실 신고하고 정지해 주세요 (G14, SUSPEND_LOST) | 이번 달 청구 금액 확인해 주세요 (G04, BILL_INQUIRY) | 다른 상담 코드 |

