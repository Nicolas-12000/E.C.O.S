-- Demo login solo para el asistente IA (requisito académico)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS demo_chat_users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username text NOT NULL UNIQUE,
    email text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    display_name text,
    created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE demo_chat_users IS 'Usuarios de demostración para POST /chat; no es auth de producto.';

-- Bayern Múnich 4–3 Real Madrid, 15 abr 2026 (vuelta); expulsión Camavinga
INSERT INTO demo_chat_users (username, email, password_hash, display_name)
VALUES (
    'camavinga',
    'camavinga@allianz2026.ecos',
    crypt('Bayern4-3', gen_salt('bf')),
    'Demo Allianz 2026'
)
ON CONFLICT (username) DO NOTHING;
