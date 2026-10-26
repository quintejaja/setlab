---
name: handoff
description: Use at the end of every work session, or when context is getting long, to save progress and write the prompt for the next session.
---

# Handoff

1. Agregar al FINAL de `PROGRESS.md` una entrada con:
   - Fecha y tarea (id de PLAN.md)
   - Qué se hizo, en 2-4 líneas
   - Decisiones tomadas y por qué (sobre todo cambios al esquema o a las reglas de dominio)
   - Bloqueos o dudas para el humano
   - Archivos clave tocados
2. Confirmar que la tarea está marcada `[x]` en `PLAN.md` y que hay commit.
3. Mostrar al humano, en un bloque de código, el prompt para la próxima sesión:

```
Leé AGENTS.md, PLAN.md y la última entrada de PROGRESS.md.
Seguí con la tarea <id>: <título>.
Contexto extra: <solo si hay algo que no esté en los archivos>.
```

4. Si hay un bloqueo que necesita decisión humana, NO generar el prompt. Explicar el bloqueo y frenar.
