# Sistema de Gestión de Empresas

## Descripción General

El sistema permite a guides crear empresas formales para gestionar equipos de guías, mantener separación entre guías independientes y empresas con equipos.

## Características Principales

### 1. Registro de Empresas

**Endpoint:** `POST /api/companies/`

**Quién puede crear:**
- Usuarios con rol `guide`
- Usuarios con rol `admin`

**Información requerida:**
- Información básica (nombre, descripción)
- Información legal (legal_name, entity_type, etc.)
- Representante legal
- Dirección y país de incorporación

### 2. Sistema de Invitaciones

**Flujo:**
1. Admin de empresa crea invitación con email del guía
2. Sistema genera código único
3. Guía recibe email con link (TODO: implementar envío)
4. Guía acepta invitación desde su cuenta
5. Se crea membresía en company_members

**Validaciones:**
- No invitaciones duplicadas pendientes
- Email debe coincidir (si se especificó)
- No exceder límite de licencia
- Usuario debe tener rol `guide`

### 3. Licenciamiento (Free Tier)

**Free Tier:**
- Hasta 5 guías por empresa
- Sin costo
- Funcionalidad completa básica

**Validaciones automáticas:**
- Al crear invitación: verifica límite
- Al aceptar invitación: verifica límite
- Al reactivar miembro: verifica límite

**Future:**
- Basic Tier: 20 guías
- Pro Tier: 50 guías
- Enterprise: ilimitado

### 4. Roles en Empresa

**Owner (Creador):**
- Permisos completos
- No puede ser removido
- Automáticamente admin

**Admin:**
- Puede invitar guías
- Puede remover miembros (excepto owner)
- Puede editar empresa

**Member:**
- Puede ver información de empresa
- Puede crear actividades/programas
- No puede invitar ni remover

## API Endpoints

### Empresas
```
POST   /api/companies/                    # Crear empresa
GET    /api/companies/                    # Listar mis empresas
GET    /api/companies/{id}                # Ver empresa
PUT    /api/companies/{id}                # Actualizar empresa
GET    /api/companies/{id}/license        # Info de licencia
```

### Invitaciones
```
POST   /api/companies/{id}/invitations     # Crear invitación
GET    /api/companies/{id}/invitations     # Listar invitaciones
POST   /api/companies/invitations/accept   # Aceptar invitación
```

### Miembros
```
GET    /api/companies/{id}/members          # Listar miembros
DELETE /api/companies/{id}/members/{user_id} # Remover miembro
```

## Frontend Routes
```
/main/:email/companies              # Lista de empresas
/main/:email/create-company         # Crear empresa
/main/:email/company/:id            # Dashboard de empresa
/accept-invitation?code=XXX         # Aceptar invitación
```

## Separación de Contextos

### Guía Independiente
- Registra datos básicos de "su empresa" en perfil
- No gestiona equipo
- Trabaja solo
- Sin límites de licencia

### Empresa Formal
- Entidad separada con registro completo
- Gestión de equipo de guías
- Sistema de invitaciones
- Límites de licencia (free: 5 guías)
- Roles y permisos

## Migración de Datos

No se requiere migración de datos existentes. Los guías actuales continúan trabajando de forma independiente. Solo cuando crean una empresa formal entran en el sistema de gestión de equipos.

## Seguridad

- Todas las operaciones requieren autenticación
- Validación de permisos en cada endpoint
- Solo admins pueden invitar/remover
- Owner no puede ser removido
- Validación de email en invitaciones

## TODO / Futuro

- [ ] Envío de emails con invitaciones
- [ ] Sistema de pagos para tiers superiores
- [ ] Dashboard con métricas de empresa
- [ ] Gestión de permisos granulares
- [ ] Audit log de acciones en empresa
- [ ] Notificaciones en app para invitaciones