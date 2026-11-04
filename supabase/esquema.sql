-- Radar de Mercados: tablas y seguridad (RLS)
create table if not exists public.activos (
  id          text primary key,            -- símbolo con "=" cambiado por "_" (GC=F -> GC_F)
  simbolo     text not null,
  orden       int  not null default 99,
  datos       jsonb not null,              -- resultado completo del motor + contexto y fuentes
  actualizado timestamptz not null default now()
);
create table if not exists public.solicitudes (
  simbolo text primary key check (simbolo ~ '^[A-Z0-9.=^-]{1,12}$'),
  pedido  timestamptz not null default now()
);
alter table public.activos enable row level security;
alter table public.solicitudes enable row level security;
-- Cualquiera puede leer el tablero; solo el dueño (por SQL / clave de servicio) escribe.
create policy "lectura publica de activos" on public.activos for select to anon, authenticated using (true);
-- Los visitantes solo pueden dejar un ticker en cola; no pueden leer ni borrar la cola.
create policy "pedir un ticker" on public.solicitudes for insert to anon, authenticated with check (true);
