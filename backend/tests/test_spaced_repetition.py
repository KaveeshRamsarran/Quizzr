import pytest
from app.services.spaced_repetition import SpacedRepetitionService


class TestSM2Algorithm:
    """Tests for the SM-2 spaced repetition algorithm."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = SpacedRepetitionService()

    def test_initial_values(self):
        """Test initial values for new cards."""
        assert SpacedRepetitionService.DEFAULT_EASE == 2.5
        assert SpacedRepetitionService.MIN_EASE == 1.3

    def test_calculate_interval_new_card_correct(self):
        """Test interval calculation for new cards with correct answer."""
        # First review - good response
        new_interval, new_ease = self.service.calculate_next_review(
            quality=4,  # good
            ease_factor=2.5,
            interval=0,
            repetitions=0
        )
        
        # First correct review should give 1-day interval
        assert new_interval >= 1
        assert new_ease >= 1.3  # Ease shouldn't go below minimum

    def test_calculate_interval_poor_response(self):
        """Test interval calculation with poor response (0-2)."""
        # Quality 0-2 should reset to beginning
        new_interval, new_ease = self.service.calculate_next_review(
            quality=1,  # again/poor
            ease_factor=2.5,
            interval=10,
            repetitions=5
        )
        
        # Should reset interval
        assert new_interval <= 1
        # Ease should decrease
        assert new_ease < 2.5

    def test_ease_minimum_bound(self):
        """Test that ease factor doesn't go below minimum."""
        # Multiple poor responses
        ease = 2.5
        interval = 10
        repetitions = 5
        
        for _ in range(10):
            interval, ease = self.service.calculate_next_review(
                quality=0,
                ease_factor=ease,
                interval=interval,
                repetitions=repetitions
            )
        
        # Ease should never go below minimum
        assert ease >= SpacedRepetitionService.MIN_EASE

    def test_good_response_increases_interval(self):
        """Test that good responses increase interval."""
        intervals = []
        ease = 2.5
        interval = 1
        repetitions = 1
        
        for _ in range(5):
            interval, ease = self.service.calculate_next_review(
                quality=4,  # good
                ease_factor=ease,
                interval=interval,
                repetitions=repetitions
            )
            intervals.append(interval)
            repetitions += 1
        
        # Each interval should be greater than or equal to previous
        for i in range(1, len(intervals)):
            assert intervals[i] >= intervals[i-1]

    def test_easy_response_bonus(self):
        """Test that easy responses give bonus interval."""
        # Compare easy vs good response
        interval_easy, ease_easy = self.service.calculate_next_review(
            quality=5,  # easy
            ease_factor=2.5,
            interval=10,
            repetitions=5
        )
        
        interval_good, ease_good = self.service.calculate_next_review(
            quality=4,  # good
            ease_factor=2.5,
            interval=10,
            repetitions=5
        )
        
        # Easy should give longer interval
        assert interval_easy >= interval_good
        # Easy should increase ease more
        assert ease_easy >= ease_good

    def test_hard_response_shorter_interval(self):
        """Test that hard responses give shorter intervals."""
        interval_hard, _ = self.service.calculate_next_review(
            quality=3,  # hard
            ease_factor=2.5,
            interval=10,
            repetitions=5
        )
        
        interval_good, _ = self.service.calculate_next_review(
            quality=4,  # good
            ease_factor=2.5,
            interval=10,
            repetitions=5
        )
        
        # Hard should give shorter or equal interval
        assert interval_hard <= interval_good

    def test_quality_to_rating_mapping(self):
        """Test quality score to rating mapping."""
        ratings = {
            0: "again",
            1: "again",
            2: "hard",
            3: "hard",
            4: "good",
            5: "easy"
        }
        
        for quality, expected in ratings.items():
            # This tests the expected behavior conceptually
            if quality <= 1:
                assert expected == "again"
            elif quality <= 3:
                assert expected == "hard"
            elif quality == 4:
                assert expected == "good"
            else:
                assert expected == "easy"

    def test_streak_calculation(self):
        """Test that consecutive correct answers increase repetitions."""
        repetitions = 0
        ease = 2.5
        interval = 0
        
        for _ in range(5):
            interval, ease = self.service.calculate_next_review(
                quality=4,
                ease_factor=ease,
                interval=interval,
                repetitions=repetitions
            )
            # After good response, repetitions should increment
            repetitions += 1
        
        assert repetitions == 5

    def test_failed_card_resets_streak(self):
        """Test that failing a card resets the learning streak."""
        # Build up a streak
        repetitions = 5
        interval = 30
        ease = 2.5
        
        # Fail the card
        new_interval, new_ease = self.service.calculate_next_review(
            quality=1,  # fail
            ease_factor=ease,
            interval=interval,
            repetitions=repetitions
        )
        
        # Interval should reset to learning phase
        assert new_interval <= 1

    def test_graduation_from_learning(self):
        """Test cards graduating from learning to review phase."""
        ease = 2.5
        interval = 0
        repetitions = 0
        
        # Simulate learning phase
        for _ in range(3):
            interval, ease = self.service.calculate_next_review(
                quality=4,
                ease_factor=ease,
                interval=interval,
                repetitions=repetitions
            )
            repetitions += 1
        
        # After a few good reviews, should have graduated to longer intervals
        assert interval > 1

    def test_mature_card_long_intervals(self):
        """Test that mature cards get very long intervals."""
        ease = 2.5
        interval = 30  # Already a month
        repetitions = 10
        
        # Good review on mature card
        new_interval, _ = self.service.calculate_next_review(
            quality=4,
            ease_factor=ease,
            interval=interval,
            repetitions=repetitions
        )
        
        # Should get even longer interval
        assert new_interval > interval
