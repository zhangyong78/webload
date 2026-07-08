from flash_earn_reminder.okx_client import parse_campaigns


SAMPLE_HTML = """
<div class="flash-earn-active-pools">
  <div class="flash-earn-campaign-card" role="button" tabindex="0">
    <div class="flash-earn-campaign-header">
      <div class="flash-earn-campaign-info">
        <img class="flash-earn-campaign-icon" src="https://example.com/robo.png" alt="ROBO"/>
        <div class="flash-earn-campaign-title">
          <h3 class="flash-earn-campaign-name">ROBO</h3>
          <div class="flash-earn-campaign-status">进行中</div>
        </div>
      </div>
      <div class="flash-earn-campaign-meta">
        <div class="flash-earn-rewards-pool"><span>总奖励</span><span>20,000,000 ROBO</span></div>
        <div class="flash-earn-ends-in"><span>结束倒计时</span><span>00 日 08 时 00 分 00 秒</span></div>
      </div>
    </div>
  </div>
</div>
"""

UPCOMING_HTML = """
<div class="flash-earn-active-pools">
  <div class="flash-earn-campaign-card" role="button" tabindex="0">
    <div class="flash-earn-campaign-header">
      <div class="flash-earn-campaign-info">
        <img class="flash-earn-campaign-icon" src="https://example.com/ai.png" alt="AI"/>
        <div class="flash-earn-campaign-title">
          <h3 class="flash-earn-campaign-name">AI</h3>
          <div class="flash-earn-campaign-status">即将上线</div>
        </div>
      </div>
      <div class="flash-earn-campaign-meta">
        <div class="flash-earn-rewards-pool"><span>总奖励</span><span>8,000,000 AI</span></div>
        <div class="flash-earn-ends-in"><span>活动即将开始</span><span>02 日 17 时 40 分 27 秒</span></div>
      </div>
    </div>
    <div class="flash-earn-pools-grid">
      <div class="flash-earn-pool-card"><div class="flash-earn-pool-type">BTC</div></div>
      <div class="flash-earn-pool-card"><div class="flash-earn-pool-type">OKSOL</div></div>
      <div class="flash-earn-pool-card"><div class="flash-earn-pool-type">OKB</div></div>
      <div class="flash-earn-pool-card"><div class="flash-earn-pool-type">AI</div></div>
    </div>
  </div>
</div>
"""

SSR_UPCOMING_HTML = """
<script id="appState" type="application/json">
{
  "appContext": {
    "initialProps": {
      "preData": {
        "flashEarnStore": {
          "flashEarnData": {
            "endedProjects": [],
            "ongoingProjects": [],
            "upcomingProjects": [
              {
                "countdownToStart": 236311000,
                "rewardDetails": [
                  {
                    "currencyIcon": "https://example.com/ai.png",
                    "currencyName": "AI",
                    "totalRewardAmount": "8000000"
                  }
                ],
                "startDateTime": "2026-07-10 15:00:00",
                "startTime": 1783666800000,
                "status": 0
              }
            ]
          }
        }
      }
    }
  }
}
</script>
<div class="flash-earn-active-pools">
  <div class="flash-earn-campaign-card" role="button" tabindex="0">
    <div class="flash-earn-campaign-header">
      <div class="flash-earn-campaign-info">
        <img class="flash-earn-campaign-icon" src="https://example.com/ai.png" alt="AI"/>
        <div class="flash-earn-campaign-title">
          <h3 class="flash-earn-campaign-name">AI</h3>
          <div class="flash-earn-campaign-status">即将上线</div>
        </div>
      </div>
      <div class="flash-earn-campaign-meta">
        <div class="flash-earn-rewards-pool"><span>总奖励</span><span>8,000,000 AI</span></div>
        <div class="flash-earn-ends-in"><span>活动即将开始</span><span>00 日 00 时 00 分 00 秒</span></div>
      </div>
    </div>
  </div>
</div>
"""


def test_parse_campaign_extracts_ongoing_status() -> None:
    campaigns = parse_campaigns(SAMPLE_HTML)

    assert len(campaigns) == 1
    assert campaigns[0].name == "ROBO"
    assert campaigns[0].status_text == "进行中"
    assert campaigns[0].reward_text == "20,000,000 ROBO"
    assert campaigns[0].is_ongoing is True
    assert campaigns[0].countdown_label == "结束倒计时"
    assert campaigns[0].countdown_seconds == 8 * 3600


def test_parse_campaign_extracts_upcoming_countdown_from_activity_starts_label() -> None:
    campaigns = parse_campaigns(UPCOMING_HTML)

    assert len(campaigns) == 1
    assert campaigns[0].name == "AI"
    assert campaigns[0].status_text == "即将上线"
    assert campaigns[0].countdown_label == "活动即将开始"
    assert campaigns[0].countdown_text == "02 日 17 时 40 分 27 秒"
    assert campaigns[0].countdown_seconds == 2 * 86400 + 17 * 3600 + 40 * 60 + 27
    assert campaigns[0].supported_assets == ("BTC", "OKSOL", "OKB", "AI")


def test_parse_campaign_prefers_ssr_appstate_countdown_over_zero_placeholder() -> None:
    campaigns = parse_campaigns(SSR_UPCOMING_HTML)

    assert len(campaigns) == 1
    assert campaigns[0].countdown_label == "活动即将开始"
    assert campaigns[0].countdown_text == "02 日 17 时 38 分 31 秒"
    assert campaigns[0].countdown_seconds == 236311
