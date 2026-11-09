from application.dashboard_service import DashboardService


def test_same_second_closures_follow_native_milliseconds_not_ticket():
    service = DashboardService()
    earlier = service._mt5_history_payload(
        dict(time=1794264015, time_msc=1794264015162, type=1,
             entry=1, profit=-51.8), 420314410, 'DEAL')
    later = service._mt5_history_payload(
        dict(time=1794264015, time_msc=1794264015911, type=1,
             entry=1, profit=28.1), 420299218, 'DEAL')
    ordered = sorted([later, earlier], key=lambda row: (row['time'], row['ticket']))
    assert [row['ticket'] for row in ordered] == [420314410, 420299218]
    assert earlier['time'].endswith('15.162000+00:00')
    assert later['time'].endswith('15.911000+00:00')


def test_deal_without_milliseconds_retains_seconds_fallback():
    service = DashboardService()
    row = service._mt5_history_payload(dict(time=1794264015, type=1), 1, 'DEAL')
    assert row['time'].endswith('15+00:00')
