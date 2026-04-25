#!/usr/bin/env python3
"""
Synapse Council v2.0 - Database Verification Tool
Verifica estado de SQLite y muestra estadísticas de debates
"""

import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

def check_database():
    """Verificar base de datos SQLite"""
    db_path = Path(__file__).parent.parent / 'data' / 'synapse.db'
    
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE BASE DE DATOS - Synapse Council v2.0")
    print("=" * 60)
    print()
    
    # Verificar existencia
    if not db_path.exists():
        print(f"❌ Base de datos NO encontrada: {db_path}")
        print("   El archivo se creará automáticamente al iniciar el servidor")
        return False
    
    print(f"✅ Base de datos encontrada: {db_path}")
    print(f"   Tamaño: {db_path.stat().st_size / 1024:.1f} KB")
    print()
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Listar todas las tablas
        print("📋 TABLAS ENCONTRADAS:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   • {table_name}: {count} registros")
        
        print()
        
        # Verificar tablas de consenso
        consensus_tables = ['consensus_debates', 'consensus_rounds', 'consensus_agent_positions']
        has_consensus = all(t in [tbl[0] for tbl in tables] for t in consensus_tables)
        
        if has_consensus:
            print("✅ Tablas de consenso: OK")
            
            # Estadísticas de debates de consenso
            cursor.execute('''
                SELECT status, COUNT(*) as count, 
                       AVG(consensus_score) as avg_score
                FROM consensus_debates 
                GROUP BY status
            ''')
            
            print("\n📊 ESTADÍSTICAS DE CONSENSO:")
            for row in cursor.fetchall():
                status, count, avg = row
                avg_pct = (avg or 0) * 100
                print(f"   • {status}: {count} debates (consenso promedio: {avg_pct:.1f}%)")
            
            # Últimos debates
            print("\n🕐 ÚLTIMOS 5 DEBATES DE CONSENSO:")
            cursor.execute('''
                SELECT id, topic, status, consensus_score, created_at, completed_at
                FROM consensus_debates 
                ORDER BY created_at DESC 
                LIMIT 5
            ''')
            
            for row in cursor.fetchall():
                debate_id, topic, status, score, created, completed = row
                score_pct = (score or 0) * 100
                print(f"\n   ID: {debate_id[:8]}...")
                print(f"   Tema: {topic[:50]}{'...' if len(topic) > 50 else ''}")
                print(f"   Estado: {status} | Consenso: {score_pct:.1f}%")
                print(f"   Creado: {created}")
                if completed:
                    print(f"   Completado: {completed}")
        else:
            print("⚠️  Tablas de consenso incompletas")
        
        # Verificar debates secuenciales
        if 'sequential_debates' in [tbl[0] for tbl in tables]:
            cursor.execute('SELECT COUNT(*) FROM sequential_debates')
            seq_count = cursor.fetchone()[0]
            print(f"\n📚 Debates secuenciales: {seq_count}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Verificación completada exitosamente")
        print("=" * 60)
        return True
        
    except sqlite3.Error as e:
        print(f"\n❌ Error de SQLite: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return False

if __name__ == '__main__':
    success = check_database()
    sys.exit(0 if success else 1)
