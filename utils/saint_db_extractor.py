import pyodbc
import pandas as pd
import os
from colorama import Fore, init

# Inicializar colores en terminal
init(autoreset=True)

print(Fore.CYAN + "=== [ETL] Motor de Extracción SAINT ERP (DevSecOps) ===")

# 1. Credenciales y Cadena de Conexión (Ajustado a tu SSMS local)
SERVER = 'localhost\\SQLEXPRESS'
DATABASE = 'EnterpriseAdminDB'
# Usamos Trusted_Connection=yes para no quemar passwords en el script (Autenticación de Windows)
CONN_STR = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'

try:
    print(Fore.YELLOW + f"[*] Conectando a {DATABASE} en {SERVER}...")
    conn = pyodbc.connect(CONN_STR)
    
    # 2. El Query Limpio (SIN 'FOR JSON AUTO', Pandas hará la magia)
    # Filtramos solo lo útil para no inyectar basura en el nuevo ERP
    query = """
    SELECT 
        CodProd AS SKU,
        LTRIM(RTRIM(Descrip)) AS Nombre,
        Precio1 AS Precio_Principal,
        Existen AS Stock,
        Marca AS Marca,
        Unidad AS Unidad_Medida,
        ACTIVO AS Activo
    FROM 
        dbo.VW_ADM_PRODUCTOS
    WHERE 
        ACTIVO = 1
    """
    
    print(Fore.YELLOW + "[*] Ejecutando extracción a nivel de memoria (Buffer)...")
    # 3. Extracción vía Pandas
    df = pd.read_sql(query, conn)
    
    # 4. Transformación y Exportación
    output_file = 'maestro_productos_saint.json'
    
    # orient='records' crea el array [{},{}] exacto que necesitas.
    # force_ascii=False respeta la "ñ" y tildes.
    df.to_json(output_file, orient='records', force_ascii=False, indent=4)
    
    print(Fore.GREEN + f"✅ [PASS] Extracción inmaculada. {len(df)} productos guardados en '{output_file}'.")

except Exception as e:
    print(Fore.RED + f"❌ [FAIL] Error crítico en el pipeline ETL: {e}")
finally:
    if 'conn' in locals():
        conn.close()
        print(Fore.CYAN + "[*] Conexión a base de datos cerrada de forma segura.")