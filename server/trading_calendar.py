"""
US Equity Trading Calendar using pandas_market_calendars
Provides accurate trading day validation excluding weekends, market holidays, and early close days
"""

from datetime import datetime, timedelta, date
from typing import List, Set, Optional, Tuple
import logging
import pandas as pd
import pandas_market_calendars as mcal

# Set up logging
calendar_logger = logging.getLogger('trading_calendar')

class USEquityTradingCalendar:
    """
    Trading calendar for US equities backed by `pandas_market_calendars`.

    Provides helpers for validating trading days, early closes, and standard
    market hours while excluding weekends and holidays.
    """
    
    def __init__(self, polygon_api_key: str = None):
        """
        Construct the trading calendar.

        Parameters
        ----------
        polygon_api_key : str, optional
            Retained for backward compatibility; unused.
        """
        # Initialize NYSE calendar from pandas_market_calendars
        self.calendar = mcal.get_calendar('NYSE')
        calendar_logger.info("📅 TRADING CALENDAR: Initialized with pandas_market_calendars NYSE calendar")
    
    def is_trading_day(self, check_date: date) -> bool:
        """
        Determine whether the supplied date is a valid trading session.

        Parameters
        ----------
        check_date : datetime.date
            Date to evaluate.

        Returns
        -------
        bool
            True when markets are open, otherwise False.
        """
        # Convert date to pandas timestamp with UTC timezone
        pd_date = pd.Timestamp(check_date, tz='UTC')
        
        # Get valid trading days for the date's year
        start = pd.Timestamp(check_date.year, 1, 1)
        end = pd.Timestamp(check_date.year, 12, 31)
        valid_days = self.calendar.valid_days(start_date=start, end_date=end)
        
        # Check if the date is in valid trading days
        return pd_date in valid_days
    
    def is_early_close_day(self, check_date: date) -> bool:
        """
        Check whether the market closes early on the provided date.

        Parameters
        ----------
        check_date : datetime.date
            Date to evaluate.

        Returns
        -------
        bool
            True when the market closes at 1:00 PM ET.
        """
        # Convert date to pandas timestamp
        pd_date = pd.Timestamp(check_date)
        
        # Get schedule for the specific date
        schedule = self.calendar.schedule(start_date=pd_date, end_date=pd_date)
        
        if pd_date in schedule.index:
            close_time = schedule.loc[pd_date, 'market_close']
            # Check if it closes at 18:00 UTC (1:00 PM ET)
            return close_time.hour == 18
        
        return False
    
    def get_market_hours(self, check_date: date) -> Optional[Tuple[datetime, datetime]]:
        """
        Retrieve the open and close timestamps for a trading day.

        Parameters
        ----------
        check_date : datetime.date
            Date to evaluate.

        Returns
        -------
        tuple[datetime.datetime, datetime.datetime] or None
            Opening and closing times in UTC, or None if markets are closed.
        """
        pd_date = pd.Timestamp(check_date)
        schedule = self.calendar.schedule(start_date=pd_date, end_date=pd_date)
        
        if pd_date in schedule.index:
            open_time = schedule.loc[pd_date, 'market_open']
            close_time = schedule.loc[pd_date, 'market_close']
            return (open_time.to_pydatetime(), close_time.to_pydatetime())
        
        return None
    
    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """
        List all trading days within an inclusive date range.

        Parameters
        ----------
        start_date : datetime.date
            Beginning of the range.
        end_date : datetime.date
            End of the range.

        Returns
        -------
        list[datetime.date]
            Trading dates within the range.
        """
        # Convert to pandas timestamps
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        
        # Get valid trading days
        valid_days = self.calendar.valid_days(start_date=start, end_date=end)
        
        # Convert back to date objects
        return [day.date() for day in valid_days]
    
    def get_trading_days_count(self, start_date: date, end_date: date) -> int:
        """
        Count the number of trading sessions within a date range.

        Parameters
        ----------
        start_date : datetime.date
            Beginning of the range.
        end_date : datetime.date
            End of the range.

        Returns
        -------
        int
            Number of trading days.
        """
        return len(self.get_trading_days(start_date, end_date))
    
    def get_next_trading_day(self, from_date: date) -> date:
        """
        Find the next trading day after the specified date.

        Parameters
        ----------
        from_date : datetime.date
            Reference date.

        Returns
        -------
        datetime.date
            Next valid trading day.
        """
        # Get valid days for the next month to ensure we find the next trading day
        start = pd.Timestamp(from_date) + pd.Timedelta(days=1)
        end = start + pd.Timedelta(days=30)
        
        valid_days = self.calendar.valid_days(start_date=start, end_date=end)
        
        if len(valid_days) > 0:
            return valid_days[0].date()
        
        # If no trading day found in 30 days, extend search
        end = start + pd.Timedelta(days=60)
        valid_days = self.calendar.valid_days(start_date=start, end_date=end)
        return valid_days[0].date() if len(valid_days) > 0 else None
    
    def get_previous_trading_day(self, from_date: date) -> date:
        """
        Find the most recent trading day prior to the supplied date.

        Parameters
        ----------
        from_date : datetime.date
            Reference date.

        Returns
        -------
        datetime.date
            Previous valid trading day.
        """
        # Get valid days for the previous month to ensure we find the previous trading day
        end = pd.Timestamp(from_date) - pd.Timedelta(days=1)
        start = end - pd.Timedelta(days=30)
        
        valid_days = self.calendar.valid_days(start_date=start, end_date=end)
        
        if len(valid_days) > 0:
            return valid_days[-1].date()
        
        # If no trading day found in 30 days, extend search
        start = end - pd.Timedelta(days=60)
        valid_days = self.calendar.valid_days(start_date=start, end_date=end)
        return valid_days[-1].date() if len(valid_days) > 0 else None
    
    def get_market_holidays(self, year: int) -> List[date]:
        """
        Enumerate US equity market holidays for a calendar year.

        Parameters
        ----------
        year : int
            Year for which to compute holidays.

        Returns
        -------
        list[datetime.date]
            Dates when the market is closed (excluding weekends).
        """
        # pandas_market_calendars doesn't directly expose holidays, 
        # but we can infer them by finding weekdays that aren't trading days
        
        # Get all valid trading days for the year
        start = pd.Timestamp(year, 1, 1)
        end = pd.Timestamp(year, 12, 31)
        valid_days = set(self.calendar.valid_days(start_date=start, end_date=end))
        
        # Known US market holidays to check (approximate dates)
        holiday_candidates = []
        
        # New Year's Day (January 1 or observed)
        ny = date(year, 1, 1)
        holiday_candidates.append(ny)
        if ny.weekday() == 5:  # Saturday
            holiday_candidates.append(ny - timedelta(days=1))
        elif ny.weekday() == 6:  # Sunday
            holiday_candidates.append(ny + timedelta(days=1))
        
        # MLK Day (3rd Monday in January)
        jan_first_monday = date(year, 1, 1)
        while jan_first_monday.weekday() != 0:
            jan_first_monday += timedelta(days=1)
        holiday_candidates.append(jan_first_monday + timedelta(days=14))
        
        # Presidents Day (3rd Monday in February)
        feb_first_monday = date(year, 2, 1)
        while feb_first_monday.weekday() != 0:
            feb_first_monday += timedelta(days=1)
        holiday_candidates.append(feb_first_monday + timedelta(days=14))
        
        # Good Friday (check March and April)
        for month in [3, 4]:
            for day in range(1, 32):
                try:
                    d = date(year, month, day)
                    if d.weekday() == 4:  # Friday
                        holiday_candidates.append(d)
                except ValueError:
                    pass
        
        # Memorial Day (last Monday in May)
        may_last = date(year, 5, 31)
        while may_last.weekday() != 0:
            may_last -= timedelta(days=1)
        holiday_candidates.append(may_last)
        
        # Juneteenth (June 19 or observed)
        if year >= 2022:
            june19 = date(year, 6, 19)
            holiday_candidates.append(june19)
            if june19.weekday() == 5:  # Saturday
                holiday_candidates.append(june19 - timedelta(days=1))
            elif june19.weekday() == 6:  # Sunday
                holiday_candidates.append(june19 + timedelta(days=1))
        
        # Independence Day (July 4 or observed)
        july4 = date(year, 7, 4)
        holiday_candidates.append(july4)
        if july4.weekday() == 5:  # Saturday
            holiday_candidates.append(july4 - timedelta(days=1))
        elif july4.weekday() == 6:  # Sunday
            holiday_candidates.append(july4 + timedelta(days=1))
        
        # Labor Day (1st Monday in September)
        sep_first_monday = date(year, 9, 1)
        while sep_first_monday.weekday() != 0:
            sep_first_monday += timedelta(days=1)
        holiday_candidates.append(sep_first_monday)
        
        # Thanksgiving (4th Thursday in November)
        nov_first_thursday = date(year, 11, 1)
        while nov_first_thursday.weekday() != 3:
            nov_first_thursday += timedelta(days=1)
        holiday_candidates.append(nov_first_thursday + timedelta(days=21))
        
        # Christmas (December 25 or observed)
        xmas = date(year, 12, 25)
        holiday_candidates.append(xmas)
        if xmas.weekday() == 5:  # Saturday
            holiday_candidates.append(xmas - timedelta(days=1))
        elif xmas.weekday() == 6:  # Sunday
            holiday_candidates.append(xmas + timedelta(days=1))
        
        # Filter to only include dates that are actually non-trading weekdays
        holidays = []
        for candidate in holiday_candidates:
            if candidate.weekday() < 5:  # Is weekday
                pd_date = pd.Timestamp(candidate, tz='UTC')
                if pd_date not in valid_days:
                    holidays.append(candidate)
        
        # Remove duplicates and sort
        holidays = sorted(list(set(holidays)))
        
        return holidays


def test_trading_calendar():
    """
    Exercise calendar helper methods and print example output.

    Returns
    -------
    None
    """
    calendar = USEquityTradingCalendar()
    
    # Test some known dates
    test_dates = [
        date(2024, 1, 1),   # New Year's Day (holiday)
        date(2024, 1, 2),   # First trading day of 2024
        date(2024, 7, 4),   # Independence Day (holiday)
        date(2024, 12, 25), # Christmas (holiday)
        date(2024, 12, 24), # Christmas Eve (should be early close)
        date(2024, 11, 29), # Day after Thanksgiving (early close)
        date(2024, 7, 3),   # Day before July 4th (might be early close)
    ]
    
    print("🧪 Testing Trading Calendar with pandas_market_calendars:")
    for test_date in test_dates:
        is_trading = calendar.is_trading_day(test_date)
        is_early_close = calendar.is_early_close_day(test_date) if is_trading else False
        
        status = "❌ Holiday/Weekend"
        if is_trading:
            status = "📍 Early Close (1:00 PM ET)" if is_early_close else "✅ Trading Day"
        
        print(f"📅 {test_date}: {status}")
    
    # Test market hours
    print("\n🕐 Market Hours for trading days:")
    for test_date in [date(2024, 12, 23), date(2024, 12, 24)]:
        hours = calendar.get_market_hours(test_date)
        if hours:
            open_time, close_time = hours
            print(f"📅 {test_date}: Opens {open_time.strftime('%I:%M %p')} UTC, Closes {close_time.strftime('%I:%M %p')} UTC")
    
    # Test date range
    start = date(2024, 12, 20)
    end = date(2024, 12, 31)
    trading_days = calendar.get_trading_days(start, end)
    print(f"\n📊 Trading days from {start} to {end}: {len(trading_days)} days")
    for day in trading_days:
        print(f"  📅 {day}")
    
    # Test holidays for 2025
    holidays_2025 = calendar.get_market_holidays(2025)
    print(f"\n🏛️ Market Holidays for 2025: {len(holidays_2025)} days")
    # Show first 10 holidays
    for holiday in holidays_2025[:10]:
        print(f"  📅 {holiday}")


if __name__ == "__main__":
    test_trading_calendar()
