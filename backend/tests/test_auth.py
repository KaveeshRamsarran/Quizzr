import pytest
from httpx import AsyncClient


class TestAuthRoutes:
    """Tests for authentication routes."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, test_user_data: dict):
        """Test successful user registration."""
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == test_user_data["email"]
        assert data["user"]["name"] == test_user_data["name"]
        assert "password" not in data["user"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user_data: dict):
        """Test registration with duplicate email fails."""
        # First registration
        await client.post("/api/v1/auth/register", json=test_user_data)
        
        # Second registration with same email
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "invalid-email",
            "password": "testpassword123",
            "name": "Test User"
        })
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """Test registration with short password fails."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "short",
            "name": "Test User"
        })
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user_data: dict):
        """Test successful login."""
        # Register first
        await client.post("/api/v1/auth/register", json=test_user_data)
        
        # Login
        response = await client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user_data: dict):
        """Test login with wrong password fails."""
        # Register first
        await client.post("/api/v1/auth/register", json=test_user_data)
        
        # Login with wrong password
        response = await client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user fails."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "testpassword123"
        })
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_authenticated(self, client: AsyncClient, authenticated_user: dict):
        """Test getting current user when authenticated."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == authenticated_user["user"]["email"]

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, client: AsyncClient):
        """Test getting current user when not authenticated fails."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user_data: dict):
        """Test refreshing access token."""
        # Register and get tokens
        register_response = await client.post("/api/v1/auth/register", json=test_user_data)
        refresh_token = register_response.json()["refresh_token"]
        
        # Refresh token
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refreshing with invalid token fails."""
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid-token"
        })
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_guest_login(self, client: AsyncClient):
        """Test guest login creates temporary account."""
        response = await client.post("/api/v1/auth/guest")
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["is_guest"] is True

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient, authenticated_user: dict):
        """Test logout invalidates token."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
