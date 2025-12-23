import pytest
from httpx import AsyncClient


class TestQuizRoutes:
    """Tests for quiz routes."""

    @pytest.mark.asyncio
    async def test_create_quiz(self, client: AsyncClient, authenticated_user: dict):
        """Test creating a new quiz."""
        response = await client.post(
            "/api/v1/quizzes",
            json={
                "title": "Test Quiz",
                "description": "A test quiz",
                "time_limit": 30,
                "passing_score": 70,
                "shuffle_questions": True
            },
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Quiz"
        assert data["time_limit"] == 30
        assert data["passing_score"] == 70

    @pytest.mark.asyncio
    async def test_list_quizzes(self, client: AsyncClient, authenticated_user: dict):
        """Test listing user's quizzes."""
        # Create quizzes
        for i in range(3):
            await client.post(
                "/api/v1/quizzes",
                json={"title": f"Quiz {i}", "description": f"Description {i}"},
                headers=authenticated_user["headers"]
            )
        
        # List quizzes
        response = await client.get(
            "/api/v1/quizzes",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_get_quiz(self, client: AsyncClient, authenticated_user: dict):
        """Test getting a specific quiz."""
        # Create quiz
        create_response = await client.post(
            "/api/v1/quizzes",
            json={"title": "Test Quiz", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        quiz_id = create_response.json()["id"]
        
        # Get quiz
        response = await client.get(
            f"/api/v1/quizzes/{quiz_id}",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Test Quiz"

    @pytest.mark.asyncio
    async def test_update_quiz(self, client: AsyncClient, authenticated_user: dict):
        """Test updating a quiz."""
        # Create quiz
        create_response = await client.post(
            "/api/v1/quizzes",
            json={"title": "Original Quiz", "description": "Original"},
            headers=authenticated_user["headers"]
        )
        quiz_id = create_response.json()["id"]
        
        # Update quiz
        response = await client.put(
            f"/api/v1/quizzes/{quiz_id}",
            json={"title": "Updated Quiz", "passing_score": 80},
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Quiz"
        assert response.json()["passing_score"] == 80

    @pytest.mark.asyncio
    async def test_delete_quiz(self, client: AsyncClient, authenticated_user: dict):
        """Test deleting a quiz."""
        # Create quiz
        create_response = await client.post(
            "/api/v1/quizzes",
            json={"title": "To Delete", "description": "Will be deleted"},
            headers=authenticated_user["headers"]
        )
        quiz_id = create_response.json()["id"]
        
        # Delete quiz
        response = await client.delete(
            f"/api/v1/quizzes/{quiz_id}",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 204
        
        # Verify deletion
        get_response = await client.get(
            f"/api/v1/quizzes/{quiz_id}",
            headers=authenticated_user["headers"]
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_question_to_quiz(self, client: AsyncClient, authenticated_user: dict):
        """Test adding a question to a quiz."""
        # Create quiz
        create_response = await client.post(
            "/api/v1/quizzes",
            json={"title": "Test Quiz", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        quiz_id = create_response.json()["id"]
        
        # Add question
        response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/questions",
            json={
                "question_text": "What is 2+2?",
                "question_type": "multiple_choice",
                "correct_answer": "4",
                "options": ["2", "3", "4", "5"],
                "points": 1
            },
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 201
        assert response.json()["question_text"] == "What is 2+2?"

    @pytest.mark.asyncio
    async def test_add_true_false_question(self, client: AsyncClient, authenticated_user: dict):
        """Test adding a true/false question."""
        # Create quiz
        create_response = await client.post(
            "/api/v1/quizzes",
            json={"title": "Test Quiz", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        quiz_id = create_response.json()["id"]
        
        # Add true/false question
        response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/questions",
            json={
                "question_text": "The sky is blue.",
                "question_type": "true_false",
                "correct_answer": "True",
                "points": 1
            },
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 201
        assert response.json()["question_type"] == "true_false"

    @pytest.mark.asyncio
    async def test_list_quiz_questions(self, client: AsyncClient, authenticated_user: dict):
        """Test listing questions in a quiz."""
        # Create quiz
        create_response = await client.post(
            "/api/v1/quizzes",
            json={"title": "Test Quiz", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        quiz_id = create_response.json()["id"]
        
        # Add questions
        for i in range(5):
            await client.post(
                f"/api/v1/quizzes/{quiz_id}/questions",
                json={
                    "question_text": f"Question {i}?",
                    "question_type": "multiple_choice",
                    "correct_answer": f"Answer {i}",
                    "options": [f"Answer {i}", "Wrong 1", "Wrong 2", "Wrong 3"],
                    "points": 1
                },
                headers=authenticated_user["headers"]
            )
        
        # Get quiz with questions
        response = await client.get(
            f"/api/v1/quizzes/{quiz_id}",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data.get("questions", [])) == 5

    @pytest.mark.asyncio
    async def test_start_quiz_attempt(self, client: AsyncClient, authenticated_user: dict):
        """Test starting a quiz attempt."""
        # Create quiz with question
        create_response = await client.post(
            "/api/v1/quizzes",
            json={"title": "Test Quiz", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        quiz_id = create_response.json()["id"]
        
        await client.post(
            f"/api/v1/quizzes/{quiz_id}/questions",
            json={
                "question_text": "Question?",
                "question_type": "multiple_choice",
                "correct_answer": "Correct",
                "options": ["Correct", "Wrong"],
                "points": 1
            },
            headers=authenticated_user["headers"]
        )
        
        # Start attempt
        response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["quiz_id"] == quiz_id
        assert data["completed"] is False

    @pytest.mark.asyncio
    async def test_submit_answer(self, client: AsyncClient, authenticated_user: dict):
        """Test submitting an answer during quiz attempt."""
        # Create quiz with question
        create_response = await client.post(
            "/api/v1/quizzes",
            json={"title": "Test Quiz", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        quiz_id = create_response.json()["id"]
        
        question_response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/questions",
            json={
                "question_text": "Question?",
                "question_type": "multiple_choice",
                "correct_answer": "Correct",
                "options": ["Correct", "Wrong"],
                "points": 1
            },
            headers=authenticated_user["headers"]
        )
        question_id = question_response.json()["id"]
        
        # Start attempt
        attempt_response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts",
            headers=authenticated_user["headers"]
        )
        attempt_id = attempt_response.json()["id"]
        
        # Submit answer
        response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts/{attempt_id}/answers",
            json={
                "question_id": question_id,
                "answer": "Correct",
                "time_spent": 5000
            },
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        assert response.json()["is_correct"] is True

    @pytest.mark.asyncio
    async def test_finish_attempt(self, client: AsyncClient, authenticated_user: dict):
        """Test finishing a quiz attempt."""
        # Create quiz
        create_response = await client.post(
            "/api/v1/quizzes",
            json={"title": "Test Quiz", "description": "Test", "passing_score": 50},
            headers=authenticated_user["headers"]
        )
        quiz_id = create_response.json()["id"]
        
        question_response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/questions",
            json={
                "question_text": "Question?",
                "question_type": "multiple_choice",
                "correct_answer": "Correct",
                "options": ["Correct", "Wrong"],
                "points": 1
            },
            headers=authenticated_user["headers"]
        )
        question_id = question_response.json()["id"]
        
        # Start attempt
        attempt_response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts",
            headers=authenticated_user["headers"]
        )
        attempt_id = attempt_response.json()["id"]
        
        # Submit correct answer
        await client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts/{attempt_id}/answers",
            json={
                "question_id": question_id,
                "answer": "Correct",
                "time_spent": 5000
            },
            headers=authenticated_user["headers"]
        )
        
        # Finish attempt
        response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts/{attempt_id}/finish",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is True
        assert data["percentage"] == 100
        assert data["passed"] is True

    @pytest.mark.asyncio
    async def test_get_quiz_attempts(self, client: AsyncClient, authenticated_user: dict):
        """Test getting all attempts for a quiz."""
        # Create quiz
        create_response = await client.post(
            "/api/v1/quizzes",
            json={"title": "Test Quiz", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        quiz_id = create_response.json()["id"]
        
        # Add a question
        await client.post(
            f"/api/v1/quizzes/{quiz_id}/questions",
            json={
                "question_text": "Question?",
                "question_type": "multiple_choice",
                "correct_answer": "Correct",
                "options": ["Correct", "Wrong"],
                "points": 1
            },
            headers=authenticated_user["headers"]
        )
        
        # Create multiple attempts
        for _ in range(3):
            await client.post(
                f"/api/v1/quizzes/{quiz_id}/attempts",
                headers=authenticated_user["headers"]
            )
        
        # Get attempts
        response = await client.get(
            f"/api/v1/quizzes/{quiz_id}/attempts",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_quiz_with_time_limit(self, client: AsyncClient, authenticated_user: dict):
        """Test quiz with time limit."""
        response = await client.post(
            "/api/v1/quizzes",
            json={
                "title": "Timed Quiz",
                "description": "Has time limit",
                "time_limit": 60
            },
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 201
        assert response.json()["time_limit"] == 60
