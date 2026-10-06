const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'


export async function getDatabaseHealth() {
  const response = await fetch(`${API_URL}/health/databases/`)

  if (!response.ok) {
    throw new Error('No se pudo consultar el backend')
  }

  return response.json()
}
