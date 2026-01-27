"""
Unit tests for checkpoint save/load functions.

Tests cover:
- Checkpoint save/load operations
- Data validation and size limits
- Error handling and rollback
- Concurrent access (row locking)
- Edge cases and security
"""
import pytest
from unittest.mock import Mock
from sqlalchemy.exc import SQLAlchemyError

from app.workers.checkpoint import (
    save_checkpoint,
    load_checkpoint,
    clear_checkpoint,
    validate_checkpoint_data,
    get_checkpoint_phase_name,
    should_resume_from_checkpoint,
    CheckpointError,
    CheckpointDataTooLargeError,
    MAX_CHECKPOINT_SIZE_BYTES,
)


class TestValidateCheckpointData:
    """Test checkpoint data validation."""

    def test_validate_valid_data(self):
        """Test validation passes for valid data."""
        checkpoint_data = {
            "collected_data": {"users": [], "incidents": []},
            "phase_durations": {"data_fetch": 12.5}
        }
        # Should not raise
        validate_checkpoint_data(checkpoint_data)

    def test_validate_rejects_non_dict(self):
        """Test validation rejects non-dict data."""
        with pytest.raises(CheckpointError, match="must be dict"):
            validate_checkpoint_data("not a dict")

        with pytest.raises(CheckpointError, match="must be dict"):
            validate_checkpoint_data([1, 2, 3])

    def test_validate_rejects_non_json_serializable(self):
        """Test validation rejects non-JSON-serializable data."""
        checkpoint_data = {
            "function": lambda x: x  # Functions are not JSON serializable
        }
        with pytest.raises(CheckpointError, match="not JSON serializable"):
            validate_checkpoint_data(checkpoint_data)

    def test_validate_rejects_too_large_data(self):
        """Test validation rejects data exceeding size limit."""
        # Create data that exceeds limit (5MB)
        large_string = "x" * (MAX_CHECKPOINT_SIZE_BYTES + 1000)
        checkpoint_data = {"large_field": large_string}

        with pytest.raises(CheckpointDataTooLargeError, match="exceeds limit"):
            validate_checkpoint_data(checkpoint_data)

    def test_validate_accepts_data_at_limit(self):
        """Test validation accepts data at size limit."""
        # Create data just under limit
        target_size = MAX_CHECKPOINT_SIZE_BYTES - 100
        # Account for JSON overhead (quotes, braces, etc.)
        string_size = target_size - 50
        data_string = "x" * string_size
        checkpoint_data = {"data": data_string}

        # Should not raise
        validate_checkpoint_data(checkpoint_data)


class TestSaveCheckpoint:
    """Test checkpoint save operations."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        db.commit = Mock()
        db.rollback = Mock()
        return db

    @pytest.fixture
    def mock_analysis(self):
        """Create mock analysis object."""
        analysis = Mock()
        analysis.id = 123
        analysis.last_checkpoint = 0
        analysis.checkpoint_data = None
        analysis.updated_at = None
        return analysis

    @pytest.mark.asyncio
    async def test_save_checkpoint_success(self, mock_db, mock_analysis):
        """Test successful checkpoint save."""
        mock_query = Mock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        checkpoint_data = {"collected_data": {"users": [1, 2, 3]}}

        await save_checkpoint(mock_db, analysis_id=123, checkpoint=1, checkpoint_data=checkpoint_data)

        # Verify analysis was updated
        assert mock_analysis.last_checkpoint == 1
        assert mock_analysis.checkpoint_data == checkpoint_data
        assert mock_analysis.updated_at is not None

        # Verify database operations
        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_checkpoint_invalid_checkpoint_number(self, mock_db):
        """Test save rejects invalid checkpoint numbers."""
        checkpoint_data = {"data": "test"}

        with pytest.raises(CheckpointError, match="Invalid checkpoint number"):
            await save_checkpoint(mock_db, analysis_id=123, checkpoint=-1, checkpoint_data=checkpoint_data)

        with pytest.raises(CheckpointError, match="Invalid checkpoint number"):
            await save_checkpoint(mock_db, analysis_id=123, checkpoint=8, checkpoint_data=checkpoint_data)

    @pytest.mark.asyncio
    async def test_save_checkpoint_analysis_not_found(self, mock_db):
        """Test save handles missing analysis."""
        mock_query = Mock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        checkpoint_data = {"data": "test"}

        with pytest.raises(CheckpointError, match="Analysis 123 not found"):
            await save_checkpoint(mock_db, analysis_id=123, checkpoint=1, checkpoint_data=checkpoint_data)

        # Rollback is called in the exception handler
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_checkpoint_invalid_data(self, mock_db, mock_analysis):
        """Test save validates data before saving."""
        mock_query = Mock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        # Non-serializable data
        checkpoint_data = {"function": lambda x: x}

        with pytest.raises(CheckpointError, match="not JSON serializable"):
            await save_checkpoint(mock_db, analysis_id=123, checkpoint=1, checkpoint_data=checkpoint_data)

        # Database should not be touched
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_checkpoint_database_error(self, mock_db, mock_analysis):
        """Test save handles database errors with rollback."""
        mock_query = Mock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        # Simulate database error on commit
        mock_db.commit.side_effect = SQLAlchemyError("Database error")

        checkpoint_data = {"data": "test"}

        with pytest.raises(CheckpointError, match="Database error saving checkpoint"):
            await save_checkpoint(mock_db, analysis_id=123, checkpoint=1, checkpoint_data=checkpoint_data)

        # Verify rollback was called
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_checkpoint_with_row_lock(self, mock_db, mock_analysis):
        """Test save uses row-level locking."""
        mock_query = Mock()
        mock_with_for_update = Mock()
        mock_query.filter.return_value.with_for_update.return_value = mock_with_for_update
        mock_with_for_update.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        checkpoint_data = {"data": "test"}

        await save_checkpoint(mock_db, analysis_id=123, checkpoint=1, checkpoint_data=checkpoint_data)

        # Verify with_for_update() was called (row lock)
        mock_query.filter.return_value.with_for_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_checkpoint_all_checkpoints(self, mock_db, mock_analysis):
        """Test save works for all valid checkpoint numbers."""
        mock_query = Mock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        checkpoint_data = {"data": "test"}

        # Test all valid checkpoints (0-7)
        for checkpoint in range(8):
            mock_db.commit.reset_mock()
            await save_checkpoint(mock_db, analysis_id=123, checkpoint=checkpoint, checkpoint_data=checkpoint_data)
            assert mock_analysis.last_checkpoint == checkpoint
            mock_db.commit.assert_called_once()


class TestLoadCheckpoint:
    """Test checkpoint load operations."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock()

    @pytest.fixture
    def mock_analysis(self):
        """Create mock analysis object."""
        analysis = Mock()
        analysis.id = 123
        analysis.last_checkpoint = 3
        analysis.checkpoint_data = {
            "collected_data": {"users": [1, 2, 3]},
            "phase_durations": {"data_fetch": 12.5}
        }
        return analysis

    @pytest.mark.asyncio
    async def test_load_checkpoint_success(self, mock_db, mock_analysis):
        """Test successful checkpoint load."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        checkpoint_data = await load_checkpoint(mock_db, analysis_id=123)

        assert checkpoint_data is not None
        assert checkpoint_data["checkpoint"] == 3
        assert "collected_data" in checkpoint_data
        assert checkpoint_data["collected_data"]["users"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_load_checkpoint_no_checkpoint_saved(self, mock_db, mock_analysis):
        """Test load returns None when no checkpoint exists."""
        mock_analysis.last_checkpoint = 0
        mock_analysis.checkpoint_data = None

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        checkpoint_data = await load_checkpoint(mock_db, analysis_id=123)

        assert checkpoint_data is None

    @pytest.mark.asyncio
    async def test_load_checkpoint_none_checkpoint(self, mock_db, mock_analysis):
        """Test load returns None when last_checkpoint is None."""
        mock_analysis.last_checkpoint = None
        mock_analysis.checkpoint_data = None

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        checkpoint_data = await load_checkpoint(mock_db, analysis_id=123)

        assert checkpoint_data is None

    @pytest.mark.asyncio
    async def test_load_checkpoint_analysis_not_found(self, mock_db):
        """Test load handles missing analysis."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        with pytest.raises(CheckpointError, match="Analysis 123 not found"):
            await load_checkpoint(mock_db, analysis_id=123)

    @pytest.mark.asyncio
    async def test_load_checkpoint_database_error(self, mock_db):
        """Test load handles database errors."""
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = SQLAlchemyError("Database error")
        mock_db.query.return_value = mock_query

        with pytest.raises(CheckpointError, match="Database error loading checkpoint"):
            await load_checkpoint(mock_db, analysis_id=123)

    @pytest.mark.asyncio
    async def test_load_checkpoint_adds_checkpoint_number(self, mock_db, mock_analysis):
        """Test load adds checkpoint number to data if missing."""
        mock_analysis.last_checkpoint = 5
        mock_analysis.checkpoint_data = {"some_data": "value"}  # No "checkpoint" key

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        checkpoint_data = await load_checkpoint(mock_db, analysis_id=123)

        assert checkpoint_data["checkpoint"] == 5

    @pytest.mark.asyncio
    async def test_load_checkpoint_preserves_existing_checkpoint_key(self, mock_db, mock_analysis):
        """Test load preserves checkpoint key if already present."""
        mock_analysis.last_checkpoint = 5
        mock_analysis.checkpoint_data = {"checkpoint": 3, "data": "value"}

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        checkpoint_data = await load_checkpoint(mock_db, analysis_id=123)

        # Should preserve existing checkpoint key
        assert checkpoint_data["checkpoint"] == 3


class TestClearCheckpoint:
    """Test checkpoint clear operations."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        db.commit = Mock()
        db.rollback = Mock()
        return db

    @pytest.fixture
    def mock_analysis(self):
        """Create mock analysis object."""
        analysis = Mock()
        analysis.id = 123
        analysis.last_checkpoint = 5
        analysis.checkpoint_data = {"some": "data"}
        return analysis

    @pytest.mark.asyncio
    async def test_clear_checkpoint_success(self, mock_db, mock_analysis):
        """Test successful checkpoint clear."""
        mock_query = Mock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        await clear_checkpoint(mock_db, analysis_id=123)

        # Verify checkpoint was cleared
        assert mock_analysis.last_checkpoint == 0
        assert mock_analysis.checkpoint_data is None

        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_checkpoint_analysis_not_found(self, mock_db):
        """Test clear handles missing analysis."""
        mock_query = Mock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        with pytest.raises(CheckpointError, match="Analysis 123 not found"):
            await clear_checkpoint(mock_db, analysis_id=123)

    @pytest.mark.asyncio
    async def test_clear_checkpoint_database_error(self, mock_db, mock_analysis):
        """Test clear handles database errors with rollback."""
        mock_query = Mock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        mock_db.commit.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(CheckpointError, match="Database error clearing checkpoint"):
            await clear_checkpoint(mock_db, analysis_id=123)

        mock_db.rollback.assert_called_once()


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_checkpoint_phase_name(self):
        """Test getting checkpoint phase names."""
        assert get_checkpoint_phase_name(0) == "starting"
        assert get_checkpoint_phase_name(1) == "data_fetch_complete"
        assert get_checkpoint_phase_name(3) == "team_analysis_complete"
        assert get_checkpoint_phase_name(7) == "complete"
        assert get_checkpoint_phase_name(99) == "unknown_99"
        assert get_checkpoint_phase_name(-1) == "unknown_-1"

    def test_should_resume_from_checkpoint(self):
        """Test resume decision logic."""
        # Checkpoint 0 (starting) - should restart
        assert should_resume_from_checkpoint(0) is False

        # Checkpoint 1+ (work done) - should resume
        assert should_resume_from_checkpoint(1) is True
        assert should_resume_from_checkpoint(2) is True
        assert should_resume_from_checkpoint(3) is True
        assert should_resume_from_checkpoint(7) is True


class TestEdgeCases:
    """Test edge cases and security scenarios."""

    @pytest.mark.asyncio
    async def test_save_checkpoint_empty_data(self):
        """Test save accepts empty but valid checkpoint data."""
        mock_db = Mock()
        mock_analysis = Mock()
        mock_analysis.id = 123

        mock_query = Mock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = mock_analysis
        mock_db.query.return_value = mock_query

        # Empty dict is valid
        checkpoint_data = {}

        await save_checkpoint(mock_db, analysis_id=123, checkpoint=1, checkpoint_data=checkpoint_data)

        mock_db.commit.assert_called_once()

    def test_validate_nested_structures(self):
        """Test validation handles deeply nested structures."""
        checkpoint_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "data": [1, 2, 3]
                        }
                    }
                }
            }
        }

        # Should not raise
        validate_checkpoint_data(checkpoint_data)

    def test_validate_unicode_data(self):
        """Test validation handles Unicode characters."""
        checkpoint_data = {
            "unicode": "Hello 世界 🌍",
            "emoji": "😀🎉🚀"
        }

        # Should not raise
        validate_checkpoint_data(checkpoint_data)

    def test_validate_special_json_values(self):
        """Test validation handles special JSON values."""
        checkpoint_data = {
            "null_value": None,
            "boolean": True,
            "number": 123.45,
            "array": [1, 2, 3],
            "empty_array": [],
            "empty_object": {}
        }

        # Should not raise
        validate_checkpoint_data(checkpoint_data)
