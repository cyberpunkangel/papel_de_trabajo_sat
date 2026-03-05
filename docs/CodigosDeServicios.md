# Códigos de servicios

Los servicios `Consulta/Query`, `Verificación/Verify` y `Descarga/Download` regresan códigos para entender el estado de la operación.

## Vista general

```mermaid
flowchart LR
    Q[Consulta / Query]
    V[Verificación / Verify]
    D[Descarga / Download]

    C1[CodEstatus]
    C2[Mensaje]
    C3[CodigoEstadoSolicitud]
    C4[EstadoSolicitud]

    Q --> C1
    Q --> C2

    V --> C1
    V --> C2
    V --> C3
    V --> C4

    D --> C1
    D --> C2
```

## `CodEstatus` (StatusCode)

`CodEstatus` y `Mensaje` están presentes en los tres servicios. En código se exponen vía `StatusCode` (`getCode()` y `getMessage()`).

```mermaid
flowchart TB
    subgraph COMUNES[Comunes en Query / Verify / Download]
        C300[300 Usuario no válido]
        C301[301 XML mal formado]
        C302[302 Sello mal formado]
        C303[303 Sello no corresponde con RFC solicitante]
        C304[304 Certificado revocado o caduco]
        C305[305 Certificado inválido]
        C5000[5000 Solicitud recibida con éxito]
    end

    subgraph QUERY[Exclusivos de Query]
        C5001[5001 Tercero no autorizado]
        C5002[5002 Solicitudes agotadas para mismos parámetros]
        C5005[5005 Solicitud duplicada]
        C5006[5006 Error interno en el proceso]
    end

    subgraph VERDOWN[Presentes en Verify y Download]
        C5004[5004 No se encontró la solicitud]
        C404[404 Error no controlado]
    end
```

| Servicio | Code | Descripción |
|---|---:|---|
| All | 300 | Usuario no válido |
| All | 301 | XML mal formado |
| All | 302 | Sello mal formado |
| All | 303 | Sello no corresponde con RfcSolicitante |
| All | 304 | Certificado revocado o caduco |
| All | 305 | Certificado inválido |
| All | 5000 | Solicitud recibida con éxito |
| Query | 5001 | Tercero no autorizado |
| Query | 5002 | Se agotó las solicitudes de por vida: Máximo para solicitudes con los mismos parámetros |
| Verify & Download | 5004 | No se encontró la solicitud |
| Query | 5005 | Solicitud duplicada: Si existe una solicitud vigente con los mismos parámetros |
| Query | 5006 | Error interno en el proceso |
| Verify & Download | 404 | Error no controlado: Reintentar más tarde la petición |

> Nota: Aunque `404` no siempre está documentado en todos los flujos, se observa en operación real.

## `CodigoEstadoSolicitud` (CodeRequest)

Aparece en `Verify`. Representa el estado de la solicitud de descarga.

```mermaid
flowchart LR
    CR5000[5000 Accepted]
    CR5002[5002 Exhausted]
    CR5003[5003 MaximumLimitReaded]
    CR5004[5004 EmptyResult]
    CR5005[5005 Duplicated]

    CR5000 --> CR5003
    CR5000 --> CR5004
    CR5000 --> CR5005
    CR5000 --> CR5002
```

| Code | Name | Descripción |
|---:|---|---|
| 5000 | Accepted | Solicitud recibida con éxito |
| 5002 | Exhausted | Se agotó las solicitudes de por vida: Máximo para solicitudes con los mismos parámetros |
| 5003 | MaximumLimitReaded | Tope máximo: Se está superando el tope máximo de CFDI o Metadata |
| 5004 | EmptyResult | No se encontró la solicitud |
| 5005 | Duplicated | Solicitud duplicada: Si existe una solicitud vigente con los mismos parámetros |

## `EstadoSolicitud` (StatusRequest)

También aparece en `Verify` y modela el ciclo de vida de la solicitud.

```mermaid
stateDiagram-v2
    [*] --> Accepted
    Accepted --> InProgress
    InProgress --> Finished
    InProgress --> Failure
    InProgress --> Rejected
    InProgress --> Expired
```

| Code | Name | Descripción |
|---:|---|---|
| 1 | Accepted | Aceptada |
| 2 | InProgress | En proceso |
| 3 | Finished | Terminada |
| 4 | Failure | Error |
| 5 | Rejected | Rechazada |
| 6 | Expired | Vencida |

