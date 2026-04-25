import sqlite3
import os

print('=== VERIFICACIÓN BASE DE DATOS ===')
print('DB existe:', os.path.exists('./data/synapse.db'))

if os.path.exists('./data/synapse.db'):
    conn = sqlite3.connect('./data/synapse.db')
    cursor = conn.cursor()
    
    print()
    print('=== TABLAS CONSENSUS ===')
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%consensus%'")
    for t in cursor.fetchall():
        count = cursor.execute(f'SELECT COUNT(*) FROM {t[0]}').fetchone()[0]
        print(f'  {t[0]}: {count} registros')
    
    print()
    print('=== ÚLTIMOS 3 CONSENSUS DEBATES ===')
    cursor.execute('SELECT id, topic, status, consensus_score, created_at, completed_at FROM consensus_debates ORDER BY created_at DESC LIMIT 3')
    for row in cursor.fetchall():
        print(f'ID: {row[0][:8]}...')
        print(f'  Tema: {row[1][:50]}')
        print(f'  Status: {row[2]}')
        print(f'  Score: {row[3]}')
        print(f'  Creado: {row[4]}')
        print(f'  Completado: {row[5]}')
        print()
    
    conn.close()
