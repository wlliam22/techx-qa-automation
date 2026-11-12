# 🗺️ Mapa de Reconocimiento Web - Docappoint (Asistente)

## 📍 Ruta: `/login`
- **URL Final:** https://docappoint-git-staging-tech-x.vercel.app/login
- **Screenshot:** `docs\docappoint_spider\screenshot_login.png`

### 🎭 Aria Snapshot
```yaml
- button
- img "Inicia Sesión"
- paragraph: Iniciar Sesión
- paragraph: Ingresa los siguientes datos para poder acceder
- paragraph: Correo / Usuario
- textbox "Ingrese aquí su correo o usuario"
- paragraph: Contraseña
- textbox "Ingrese aquí su contraseña"
- button
- checkbox "Recuérdame"
- text: Recuérdame
- paragraph: ¿Olvidaste tu contraseña?
- button "Iniciar Sesión"
- complementary "Aviso de confidencialidad":
  - heading "Aviso de confidencialidad" [level=2]
  - paragraph: La información de salud de los pacientes en Docappoint es confidencial. Los cambios que hagas y los documentos que abras quedan registrados.
- paragraph:
  - text: ¿Aún no tienes una cuenta?
  - link "Da click aquí para registrarte":
    - /url: /register
- img "Inicia Sesión"
- button "notificaciones": "0"
```

---

## 📍 Ruta: `/terminos-y-condiciones`
- **URL Final:** https://docappoint-git-staging-tech-x.vercel.app/terminos-y-condiciones
- **Screenshot:** `docs\docappoint_spider\screenshot_terminos-y-condiciones.png`

### 🎭 Aria Snapshot
```yaml
- img
- list:
  - button "Doctores Doctores Asociados":
    - img "Doctores"
    - paragraph: Doctores Asociados
  - button "Consultorios":
    - img
    - paragraph: Consultorios
  - button "Citas":
    - img
    - paragraph: Citas
  - button "Chats Mensajes":
    - img "Chats"
    - paragraph: Mensajes
- button "Cerrar todas mis sesiones":
  - paragraph: Cerrar todas mis sesiones
- button "Cerrar Sesión":
  - img
  - paragraph: Cerrar Sesión
- main:
  - heading "Términos y condiciones de uso de DocAppoint" [level=1]
  - paragraph: "Última actualización: 30/03/2026"
  - heading "1. Aceptación de los términos" [level=2]
  - paragraph:
    - text: Bienvenido a DocAppoint (en adelante, la "Plataforma"), operada por DocAppoint (en adelante, la "Empresa" o "Nosotros"). Al acceder, navegar o utilizar nuestro sitio web
    - link "www.docappoint.com.mx":
      - /url: https://www.docappoint.com.mx
    - text: y cualquier aplicación asociada, usted acepta estar legalmente vinculado por estos Términos y Condiciones. Si no está de acuerdo, por favor absténgase de utilizar el servicio.
  - heading "2. Descripción del servicio y alcance" [level=2]
  - paragraph: "DocAppoint es una plataforma tecnológica en la nube (SaaS) que provee herramientas administrativas para la gestión de consultorios médicos, expedientes clínicos electrónicos y la intermediación de citas entre:"
  - list:
    - listitem: Pacientes.
    - listitem: Profesionales de la Salud (Médicos, Terapeutas, Nutriólogos, etc.).
    - listitem: Laboratorios Clínicos.
  - paragraph: "LIMITACIÓN DEL SERVICIO: DocAppoint provee exclusivamente la infraestructura tecnológica. NO prestamos servicios médicos, no emitimos diagnósticos, ni interpretamos estudios de laboratorio."
  - heading "3. Telemedicina y servicios de terceros" [level=2]
  - paragraph: "La Plataforma facilita la coordinación de consultas a distancia (\"Telemedicina\") mediante la generación y compartición de enlaces a servicios de videoconferencia de terceros. Al utilizar esta función, el Usuario reconoce y acepta que:"
  - list:
    - listitem: "Proveedor Externo: La videollamada se realiza fuera de la infraestructura de DocAppoint. No tenemos control sobre la calidad, disponibilidad, seguridad o funcionamiento de Google Meet."
    - listitem: "Exoneración: DocAppoint no será responsable por fallas técnicas, interrupciones de la llamada, o vulneraciones de seguridad que ocurran dentro de los servidores de terceros."
    - listitem: "Responsabilidad Médica: El Profesional de la Salud es el único responsable de determinar si la condición del paciente puede ser atendida vía remota y de cumplir con las Normas Oficiales Mexicanas aplicables a la atención médica a distancia, incluyendo la obtención del consentimiento informado del paciente antes de la sesión."
  - heading "4. Cuentas y registro" [level=2]
  - heading "4.1. Profesionales de la Salud" [level=3]
  - paragraph: Para contratar el servicio, el Profesional debe acreditar contar con Cédula Profesional vigente para ejercer en México. DocAppoint se reserva el derecho de suspender cuentas que no validen sus credenciales ante COFEPRIS/SEP si así fuera requerido por la autoridad.
  - heading "4.2. Pacientes" [level=3]
  - paragraph: El Paciente se compromete a proporcionar información veraz sobre su estado de salud e identidad. El uso de identidades falsas para obtener medicamentos controlados será reportado a las autoridades.
  - heading "5. Suscripciones y pagos" [level=2]
  - paragraph: El uso de la Plataforma para Profesionales de la Salud y Laboratorios está sujeto al pago de una suscripción.
  - list:
    - listitem: "Suscripción: El servicio se cobra bajo un modelo de suscripción recurrente (Mensual o Anual)."
    - listitem: "Pago por adelantado: El servicio se paga por adelantado. El ciclo de facturación comienza el día que se realiza el pago."
    - listitem: "Falta de Pago: En caso de que el método de pago sea rechazado o la suscripción no sea renovada, DocAppoint se reserva el derecho de suspender temporalmente el acceso al panel administrativo hasta que se regularice el saldo."
    - listitem: "Cambios de Precio: Nos reservamos el derecho de modificar las tarifas de suscripción, notificando al usuario con al menos 30 días de anticipación vía correo electrónico."
    - listitem: "Facturación: Es responsabilidad del Usuario solicitar su Comprobante Fiscal Digital por Internet (CFDI) dentro del mes en curso en el que realizó el pago. (pendiente a confirmar)."
  - heading "6. Propiedad de los datos y expediente clínico" [level=2]
  - list:
    - listitem: "Propiedad Intelectual: El código fuente, diseño y marca DocAppoint son propiedad de la Empresa."
    - listitem: "Propiedad de los Datos Clínicos: En cumplimiento con la NOM-004-SSA3-2012, la información contenida en el Expediente Clínico Electrónico es propiedad del Paciente. El Profesional de la Salud actúa como custodio legal de dicha información y DocAppoint actúa como encargado del tratamiento y almacenamiento seguro (Hosting)."
    - listitem: "Portabilidad: En caso de que el Profesional de la Salud decida cancelar su suscripción, DocAppoint proporcionará un mecanismo para que pueda descargar/exportar los expedientes clínicos de sus pacientes en un formato legible, garantizando la continuidad de la atención médica."
  - heading "7. Responsabilidad y deslinde" [level=2]
... (27 líneas más. Ver HTML completo)

```

---

## 📍 Ruta: `/citas`
- **URL Final:** https://docappoint-git-staging-tech-x.vercel.app/citas
- **Screenshot:** `docs\docappoint_spider\screenshot_citas.png`

### 🎭 Aria Snapshot
```yaml
- 'heading "Médicos en Citas: agenda tu cita en línea" [level=1]'
- img
- list:
  - button "Doctores Doctores Asociados":
    - img "Doctores"
    - paragraph: Doctores Asociados
  - button "Consultorios":
    - img
    - paragraph: Consultorios
  - button "Citas":
    - img
    - paragraph: Citas
  - button "Chats Mensajes":
    - img "Chats"
    - paragraph: Mensajes
- button "Cerrar todas mis sesiones":
  - paragraph: Cerrar todas mis sesiones
- button "Cerrar Sesión":
  - img
  - paragraph: Cerrar Sesión
- paragraph: ¡Hola, Mario!
- paragraph: Docappoint le desea un excelente día
- paragraph:
  - text: En esta sección encontrará nuestros médicos asociados con
  - strong: Docappoint
  - text: .
- paragraph: 17:35 PM 11 de Noviembre de 2026
- paragraph:
  - img
  - text: "Filtros:"
- combobox "Especialidad":
  - emphasis: Especialidad
- combobox "Citas"
- link "Ver laboratorios →":
  - /url: /laboratorios
- textbox "Buscar por nombre o especialidad":
  - /placeholder: Buscar por nombre o especialidad...
- heading "No se encontraron doctores" [level=6]
- paragraph: No hay doctores disponibles en esta categoría o región. Intenta con otros filtros.
- navigation "pagination navigation":
  - list:
    - listitem:
      - button "Go to first page" [disabled]
    - listitem:
      - button "Go to previous page" [disabled]
    - listitem:
      - button "Go to next page" [disabled]
    - listitem:
      - button "Go to last page" [disabled]
- paragraph: ©Docappoint 2026, Todos los derechos reservados
- button "notificaciones": "0"
```

---

## 📍 Ruta: `/mensajes`
- **URL Final:** https://docappoint-git-staging-tech-x.vercel.app/mensajes
- **Screenshot:** `docs\docappoint_spider\screenshot_mensajes.png`

### 🎭 Aria Snapshot
```yaml
- 'heading "Médicos en Mensajes: agenda tu cita en línea" [level=1]'
- img
- list:
  - button "Doctores Doctores Asociados":
    - img "Doctores"
    - paragraph: Doctores Asociados
  - button "Consultorios":
    - img
    - paragraph: Consultorios
  - button "Citas":
    - img
    - paragraph: Citas
  - button "Chats Mensajes":
    - img "Chats"
    - paragraph: Mensajes
- button "Cerrar todas mis sesiones":
  - paragraph: Cerrar todas mis sesiones
- button "Cerrar Sesión":
  - img
  - paragraph: Cerrar Sesión
- paragraph: ¡Hola, Mario!
- paragraph: Docappoint le desea un excelente día
- paragraph:
  - text: En esta sección encontrará nuestros médicos asociados con
  - strong: Docappoint
  - text: .
- paragraph: 17:35 PM 11 de Noviembre de 2026
- paragraph:
  - img
  - text: "Filtros:"
- combobox "Especialidad":
  - emphasis: Especialidad
- combobox "Mensajes"
- link "Ver laboratorios →":
  - /url: /laboratorios
- textbox "Buscar por nombre o especialidad":
  - /placeholder: Buscar por nombre o especialidad...
- heading "No se encontraron doctores" [level=6]
- paragraph: No hay doctores disponibles en esta categoría o región. Intenta con otros filtros.
- navigation "pagination navigation":
  - list:
    - listitem:
      - button "Go to first page" [disabled]
    - listitem:
      - button "Go to previous page" [disabled]
    - listitem:
      - button "Go to next page" [disabled]
    - listitem:
      - button "Go to last page" [disabled]
- paragraph: ©Docappoint 2026, Todos los derechos reservados
- button "notificaciones": "0"
```

---

