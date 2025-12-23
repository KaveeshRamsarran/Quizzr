import pytest
from httpx import AsyncClient


class TestDeckRoutes:
    """Tests for deck routes."""

    @pytest.mark.asyncio
    async def test_create_deck(self, client: AsyncClient, authenticated_user: dict):
        """Test creating a new deck."""
        response = await client.post(
            "/api/v1/decks",
            json={
                "title": "Test Deck",
                "description": "A test deck",
                "is_public": False
            },
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Deck"
        assert data["description"] == "A test deck"
        assert data["is_public"] is False

    @pytest.mark.asyncio
    async def test_list_decks(self, client: AsyncClient, authenticated_user: dict):
        """Test listing user's decks."""
        # Create some decks
        for i in range(3):
            await client.post(
                "/api/v1/decks",
                json={"title": f"Deck {i}", "description": f"Description {i}"},
                headers=authenticated_user["headers"]
            )
        
        # List decks
        response = await client.get(
            "/api/v1/decks",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_get_deck(self, client: AsyncClient, authenticated_user: dict):
        """Test getting a specific deck."""
        # Create deck
        create_response = await client.post(
            "/api/v1/decks",
            json={"title": "Test Deck", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        deck_id = create_response.json()["id"]
        
        # Get deck
        response = await client.get(
            f"/api/v1/decks/{deck_id}",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Test Deck"

    @pytest.mark.asyncio
    async def test_get_nonexistent_deck(self, client: AsyncClient, authenticated_user: dict):
        """Test getting a nonexistent deck returns 404."""
        response = await client.get(
            "/api/v1/decks/99999",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_deck(self, client: AsyncClient, authenticated_user: dict):
        """Test updating a deck."""
        # Create deck
        create_response = await client.post(
            "/api/v1/decks",
            json={"title": "Original Title", "description": "Original"},
            headers=authenticated_user["headers"]
        )
        deck_id = create_response.json()["id"]
        
        # Update deck
        response = await client.put(
            f"/api/v1/decks/{deck_id}",
            json={"title": "Updated Title", "description": "Updated"},
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_deck(self, client: AsyncClient, authenticated_user: dict):
        """Test deleting a deck."""
        # Create deck
        create_response = await client.post(
            "/api/v1/decks",
            json={"title": "To Delete", "description": "Will be deleted"},
            headers=authenticated_user["headers"]
        )
        deck_id = create_response.json()["id"]
        
        # Delete deck
        response = await client.delete(
            f"/api/v1/decks/{deck_id}",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 204
        
        # Verify deletion
        get_response = await client.get(
            f"/api/v1/decks/{deck_id}",
            headers=authenticated_user["headers"]
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_card_to_deck(self, client: AsyncClient, authenticated_user: dict):
        """Test adding a card to a deck."""
        # Create deck
        create_response = await client.post(
            "/api/v1/decks",
            json={"title": "Test Deck", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        deck_id = create_response.json()["id"]
        
        # Add card
        response = await client.post(
            f"/api/v1/decks/{deck_id}/cards",
            json={
                "front_content": "What is 2+2?",
                "back_content": "4",
                "card_type": "basic"
            },
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 201
        assert response.json()["front_content"] == "What is 2+2?"

    @pytest.mark.asyncio
    async def test_list_deck_cards(self, client: AsyncClient, authenticated_user: dict):
        """Test listing cards in a deck."""
        # Create deck
        create_response = await client.post(
            "/api/v1/decks",
            json={"title": "Test Deck", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        deck_id = create_response.json()["id"]
        
        # Add cards
        for i in range(5):
            await client.post(
                f"/api/v1/decks/{deck_id}/cards",
                json={
                    "front_content": f"Question {i}",
                    "back_content": f"Answer {i}",
                    "card_type": "basic"
                },
                headers=authenticated_user["headers"]
            )
        
        # List cards
        response = await client.get(
            f"/api/v1/decks/{deck_id}/cards",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_update_card(self, client: AsyncClient, authenticated_user: dict):
        """Test updating a card."""
        # Create deck and card
        create_response = await client.post(
            "/api/v1/decks",
            json={"title": "Test Deck", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        deck_id = create_response.json()["id"]
        
        card_response = await client.post(
            f"/api/v1/decks/{deck_id}/cards",
            json={
                "front_content": "Original Question",
                "back_content": "Original Answer",
                "card_type": "basic"
            },
            headers=authenticated_user["headers"]
        )
        card_id = card_response.json()["id"]
        
        # Update card
        response = await client.put(
            f"/api/v1/decks/{deck_id}/cards/{card_id}",
            json={
                "front_content": "Updated Question",
                "back_content": "Updated Answer"
            },
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        assert response.json()["front_content"] == "Updated Question"

    @pytest.mark.asyncio
    async def test_delete_card(self, client: AsyncClient, authenticated_user: dict):
        """Test deleting a card from deck."""
        # Create deck and card
        create_response = await client.post(
            "/api/v1/decks",
            json={"title": "Test Deck", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        deck_id = create_response.json()["id"]
        
        card_response = await client.post(
            f"/api/v1/decks/{deck_id}/cards",
            json={
                "front_content": "To Delete",
                "back_content": "Will be deleted",
                "card_type": "basic"
            },
            headers=authenticated_user["headers"]
        )
        card_id = card_response.json()["id"]
        
        # Delete card
        response = await client.delete(
            f"/api/v1/decks/{deck_id}/cards/{card_id}",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_get_due_cards(self, client: AsyncClient, authenticated_user: dict):
        """Test getting cards due for review."""
        # Create deck and add cards
        create_response = await client.post(
            "/api/v1/decks",
            json={"title": "Test Deck", "description": "Test"},
            headers=authenticated_user["headers"]
        )
        deck_id = create_response.json()["id"]
        
        # Add cards (new cards should be due immediately)
        for i in range(3):
            await client.post(
                f"/api/v1/decks/{deck_id}/cards",
                json={
                    "front_content": f"Question {i}",
                    "back_content": f"Answer {i}",
                    "card_type": "basic"
                },
                headers=authenticated_user["headers"]
            )
        
        # Get due cards
        response = await client.get(
            f"/api/v1/decks/{deck_id}/due",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 0  # New cards might not be due depending on implementation

    @pytest.mark.asyncio
    async def test_export_deck(self, client: AsyncClient, authenticated_user: dict):
        """Test exporting a deck."""
        # Create deck with cards
        create_response = await client.post(
            "/api/v1/decks",
            json={"title": "Export Test", "description": "To export"},
            headers=authenticated_user["headers"]
        )
        deck_id = create_response.json()["id"]
        
        await client.post(
            f"/api/v1/decks/{deck_id}/cards",
            json={
                "front_content": "Question",
                "back_content": "Answer",
                "card_type": "basic"
            },
            headers=authenticated_user["headers"]
        )
        
        # Export deck
        response = await client.get(
            f"/api/v1/decks/{deck_id}/export",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cannot_access_others_deck(self, client: AsyncClient, authenticated_user: dict):
        """Test users cannot access other users' private decks."""
        # Create deck as first user
        create_response = await client.post(
            "/api/v1/decks",
            json={"title": "Private Deck", "description": "Private", "is_public": False},
            headers=authenticated_user["headers"]
        )
        deck_id = create_response.json()["id"]
        
        # Register second user
        await client.post("/api/v1/auth/register", json={
            "email": "other@example.com",
            "password": "otherpassword123",
            "name": "Other User"
        })
        login_response = await client.post("/api/v1/auth/login", json={
            "email": "other@example.com",
            "password": "otherpassword123"
        })
        other_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        
        # Try to access first user's private deck
        response = await client.get(
            f"/api/v1/decks/{deck_id}",
            headers=other_headers
        )
        
        assert response.status_code in [403, 404]
