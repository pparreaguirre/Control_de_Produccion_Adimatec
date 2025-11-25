# dashboard_final_mobile.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import requests
from PIL import Image
import io

# Limpiar cache completo (agregar al principio del código)
st.cache_data.clear()

# Configuración de la página para móviles
st.set_page_config(
    page_title="Dashboard de Producción - Adimatec",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar logo
@st.cache_data
def load_logo(url):
    try:
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content))
        return image
    except:
        return None

logo = load_logo("https://i.postimg.cc/hjfVhfXf/Logo-Adimatec.jpg")

# Título principal con logo
col_logo, col_title, col_icon = st.columns([1, 3, 1])
with col_logo:
    if logo:
        st.image(logo, width=100)
with col_title:
    st.title("Dashboard de Producción - Adimatec")
with col_icon:
    st.markdown(
        """
        <div style='text-align: right; margin-top: 20px;'>
            <span style='font-size: 2em;'>🏭</span>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

@st.cache_data(ttl=3600)
def load_data():
    """Cargar datos desde Google Sheets"""
    try:
        # Sheet ID (la parte larga después de /d/)
        sheet_id = "17eEYewfzoBZXkFWBm5DOJp3IuvHg9WvN"
        
        # URLs CORREGIDAS - formato de exportación directa
        ot_master_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=525532145"
        procesos_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=240160734"
        
        # Cargar datos
        ot_master = pd.read_csv(ot_master_csv)
        procesos = pd.read_csv(procesos_csv)
        
        return ot_master, procesos
    except Exception as e:
        st.error(f"Error al cargar los datos desde Google Sheets: {e}")
        return None, None

# Cargar datos
ot_master, procesos = load_data()

if ot_master is None or procesos is None:
    st.stop()

# CORREGIDO: Asegurar que la columna 'ot' sea string en ambos dataframes desde el inicio
ot_master['ot'] = ot_master['ot'].astype(str)
procesos['ot'] = procesos['ot'].astype(str)

# Sidebar con filtros
st.sidebar.header("🔍 Filtros")

# Convertir fechas en ot_master
date_columns = ['fecha_entrega', 'fecha_impresion', 'fecha_terminado', 'fecha_entregada']
for col in date_columns:
    if col in ot_master.columns:
        ot_master[col] = pd.to_datetime(ot_master[col], errors='coerce')

# Convertir fechas en procesos
date_columns_procesos = ['fecha_inicio_1', 'fecha_inicio_2']
for col in date_columns_procesos:
    if col in procesos.columns:
        procesos[col] = pd.to_datetime(procesos[col], errors='coerce')

# Filtros principales
clientes = ['Todos'] + sorted(ot_master['cliente'].dropna().unique().tolist())
cliente_seleccionado = st.sidebar.selectbox("Cliente", clientes)

estatus_options = ['Todos'] + sorted(ot_master['estatus'].dropna().unique().tolist())
estatus_seleccionado = st.sidebar.selectbox("Estatus", estatus_options)

# Filtro de OT - CORREGIDO: Asegurar tipo de dato consistente
ots = ["Todas"] + sorted(ot_master['ot'].astype(str).unique().tolist())
ot_seleccionada = st.sidebar.selectbox("OT", ots)

# CORREGIDO: Filtros de empleados SIN REPETIDOS
st.sidebar.subheader("👥 Filtros por Empleados")

# Función para limpiar y normalizar nombres
def limpiar_nombre(nombre):
    if pd.isna(nombre):
        return None
    # Convertir a string, quitar espacios extras, y capitalizar
    return str(nombre).strip().title()

# Obtener lista única de empleados de ambas columnas (limpiando los nombres)
empleados_1 = [limpiar_nombre(x) for x in procesos['empleado_1'].dropna().unique()]
empleados_2 = [limpiar_nombre(x) for x in procesos['empleado_2'].dropna().unique()]

# Combinar y eliminar duplicados y valores None
todos_empleados = list(set([emp for emp in empleados_1 + empleados_2 if emp is not None]))
todos_empleados = ['Todos'] + sorted(todos_empleados)

empleado_seleccionado = st.sidebar.selectbox("Empleado", todos_empleados)

# Filtro de fechas
st.sidebar.subheader("📅 Filtro por Fecha de Entrega")
min_date = ot_master['fecha_entrega'].min()
max_date = ot_master['fecha_entrega'].max()
if pd.notna(min_date) and pd.notna(max_date):
    fecha_inicio = st.sidebar.date_input("Fecha inicio", min_date)
    fecha_fin = st.sidebar.date_input("Fecha fin", max_date)
else:
    st.sidebar.warning("No hay fechas válidas para filtrar")
    fecha_inicio = None
    fecha_fin = None

# CORREGIDO: Aplicar filtros de manera consistente
ot_master_filtrado = ot_master.copy()
procesos_filtrados = procesos.copy()

if cliente_seleccionado != 'Todos':
    ot_master_filtrado = ot_master_filtrado[ot_master_filtrado['cliente'] == cliente_seleccionado]
    procesos_filtrados = procesos_filtrados[procesos_filtrados['ot'].isin(ot_master_filtrado['ot'])]

if estatus_seleccionado != 'Todos':
    ot_master_filtrado = ot_master_filtrado[ot_master_filtrado['estatus'] == estatus_seleccionado]
    procesos_filtrados = procesos_filtrados[procesos_filtrados['ot'].isin(ot_master_filtrado['ot'])]

# CORREGIDO: Filtro de OT - Aplicar a ambos dataframes de manera consistente
if ot_seleccionada != 'Todas':
    ot_master_filtrado = ot_master_filtrado[ot_master_filtrado['ot'] == ot_seleccionada]
    procesos_filtrados = procesos_filtrados[procesos_filtrados['ot'] == ot_seleccionada]

# CORREGIDO: Aplicar filtro de empleado (comparando con nombres limpios)
if empleado_seleccionado != 'Todos':
    # Crear columnas temporales con nombres limpios para comparar
    procesos_temp = procesos_filtrados.copy()
    procesos_temp['empleado_1_clean'] = procesos_temp['empleado_1'].apply(limpiar_nombre)
    procesos_temp['empleado_2_clean'] = procesos_temp['empleado_2'].apply(limpiar_nombre)
    
    procesos_filtrados = procesos_temp[
        (procesos_temp['empleado_1_clean'] == empleado_seleccionado) | 
        (procesos_temp['empleado_2_clean'] == empleado_seleccionado)
    ]
    # Eliminar columnas temporales
    procesos_filtrados = procesos_filtrados.drop(['empleado_1_clean', 'empleado_2_clean'], axis=1)
    
    ot_master_filtrado = ot_master_filtrado[ot_master_filtrado['ot'].isin(procesos_filtrados['ot'])]

if fecha_inicio and fecha_fin:
    ot_master_filtrado = ot_master_filtrado[
        (ot_master_filtrado['fecha_entrega'] >= pd.Timestamp(fecha_inicio)) &
        (ot_master_filtrado['fecha_entrega'] <= pd.Timestamp(fecha_fin))
    ]
    procesos_filtrados = procesos_filtrados[procesos_filtrados['ot'].isin(ot_master_filtrado['ot'])]

# Definir estados que NO se consideran vencidos (estados finalizados)
estados_no_vencidos = ['FACTURADO', 'OK', 'OK NO ENTREGADO']

# Calcular OTs vencidas y por vencer
hoy = datetime.now()
ot_master_filtrado['estado_entrega'] = ot_master_filtrado.apply(
    lambda row: 
        'Completada' if row['estatus'] in estados_no_vencidos else
        'Vencida' if pd.notna(row['fecha_entrega']) and row['fecha_entrega'] < hoy else 
        'Por vencer' if pd.notna(row['fecha_entrega']) and row['fecha_entrega'] >= hoy and row['fecha_entrega'] <= hoy + timedelta(days=7) else 
        'En plazo',
    axis=1
)

# Calcular porcentaje de facturación
total_ots = len(ot_master_filtrado)
ots_facturadas = len(ot_master_filtrado[ot_master_filtrado['estatus'] == 'FACTURADO'])
porcentaje_facturado = (ots_facturadas / total_ots * 100) if total_ots > 0 else 0

# Identificar reprocesos (Garantías)
if 'orden_compra' in ot_master_filtrado.columns:
    ot_master_filtrado['es_reproceso'] = ot_master_filtrado['orden_compra'].str.contains('GARANTIA', case=False, na=False)
    total_reprocesos = ot_master_filtrado['es_reproceso'].sum()
    porcentaje_reprocesos = (total_reprocesos / total_ots * 100) if total_ots > 0 else 0
else:
    total_reprocesos = 0
    porcentaje_reprocesos = 0

# NUEVO: Calcular desviaciones de horas
if 'horas_estimadas_ot' in ot_master_filtrado.columns and 'horas_reales_ot' in ot_master_filtrado.columns:
    # Filtrar solo OTs con horas válidas
    ot_con_horas = ot_master_filtrado[
        (ot_master_filtrado['horas_estimadas_ot'].notna()) & 
        (ot_master_filtrado['horas_reales_ot'].notna())
    ].copy()
    
    # Calcular desviaciones
    ot_con_horas['diferencia_horas'] = ot_con_horas['horas_reales_ot'] - ot_con_horas['horas_estimadas_ot']
    ot_con_horas['tipo_desviacion'] = ot_con_horas['diferencia_horas'].apply(
        lambda x: 'Desviación Positiva' if x <= 0 else 'Desviación Negativa'
    )
    
    # Calcular totales
    total_horas_programadas = ot_con_horas['horas_estimadas_ot'].sum()
    horas_desviacion_positiva = ot_con_horas[ot_con_horas['tipo_desviacion'] == 'Desviación Positiva']['horas_reales_ot'].sum()
    horas_desviacion_negativa = ot_con_horas[ot_con_horas['tipo_desviacion'] == 'Desviación Negativa']['horas_reales_ot'].sum()
    
    # Calcular porcentajes
    porcentaje_positivo = (horas_desviacion_positiva / total_horas_programadas * 100) if total_horas_programadas > 0 else 0
    porcentaje_negativo = (horas_desviacion_negativa / total_horas_programadas * 100) if total_horas_programadas > 0 else 0
else:
    total_horas_programadas = 0
    horas_desviacion_positiva = 0
    horas_desviacion_negativa = 0
    porcentaje_positivo = 0
    porcentaje_negativo = 0

# Métricas principales
st.header("📊 Métricas Principales")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Total OTs", total_ots)

with col2:
    ots_en_proceso = len(ot_master_filtrado[ot_master_filtrado['estatus'] == 'EN PROCESO'])
    st.metric("OTs en Proceso", ots_en_proceso)

with col3:
    st.metric("OTs Facturadas", ots_facturadas)

with col4:
    ots_vencidas = len(ot_master_filtrado[
        (ot_master_filtrado['estado_entrega'] == 'Vencida') & 
        (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))
    ])
    st.metric("OTs Vencidas", ots_vencidas, delta=-ots_vencidas, delta_color="inverse")

with col5:
    ots_por_vencer = len(ot_master_filtrado[
        (ot_master_filtrado['estado_entrega'] == 'Por vencer') & 
        (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))
    ])
    st.metric("OTs por Vencer", ots_por_vencer, delta=ots_por_vencer, delta_color="off")

with col6:
    st.metric("% Facturación", f"{porcentaje_facturado:.1f}%")

st.markdown("---")

# GRÁFICO PRINCIPAL: OTs VENCIDAS Y POR VENCER
st.header("📅 Estado de Entregas - OTs Vencidas y Por Vencer")

estado_entrega_counts = ot_master_filtrado['estado_entrega'].value_counts()
estados_interes = ['Vencida', 'Por vencer']
estado_entrega_counts_filtrado = estado_entrega_counts[estado_entrega_counts.index.isin(estados_interes)]

if not estado_entrega_counts_filtrado.empty:
    fig = px.bar(
        x=estado_entrega_counts_filtrado.index,
        y=estado_entrega_counts_filtrado.values,
        title="OTs Vencidas y Por Vencer (Solo OTs Activas)",
        labels={'x': 'Estado de Entrega', 'y': 'Cantidad de OTs'},
        color=estado_entrega_counts_filtrado.index,
        color_discrete_map={'Vencida': '#FF4B4B', 'Por vencer': '#FFA500'},
        text=estado_entrega_counts_filtrado.values
    )
    
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    fig.update_layout(
        showlegend=False,
        yaxis_title="Cantidad de OTs",
        xaxis_title="",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay OTs vencidas o por vencer con los filtros actuales.")

# Detalle de OTs vencidas y por vencer
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 OTs Vencidas (Solo Activas)")
    ots_vencidas_df = ot_master_filtrado[
        (ot_master_filtrado['estado_entrega'] == 'Vencida') & 
        (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))
    ][['ot', 'cliente', 'fecha_entrega', 'estatus']]
    if not ots_vencidas_df.empty:
        st.dataframe(ots_vencidas_df, use_container_width=True, height=200)
        st.caption(f"Total OTs vencidas activas: {len(ots_vencidas_df)}")
    else:
        st.info("No hay OTs vencidas activas")

with col2:
    st.subheader("📋 OTs por Vencer (Próximos 7 días, Solo Activas)")
    ots_por_vencer_df = ot_master_filtrado[
        (ot_master_filtrado['estado_entrega'] == 'Por vencer') & 
        (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))
    ][['ot', 'cliente', 'fecha_entrega', 'estatus']]
    if not ots_por_vencer_df.empty:
        st.dataframe(ots_por_vencer_df, use_container_width=True, height=200)
        st.caption(f"Total OTs por vencer activas: {len(ots_por_vencer_df)}")
    else:
        st.info("No hay OTs por vencer activas")

# OTs Completadas
st.markdown("---")
st.header("✅ OTs Completadas")

ots_completadas_df = ot_master_filtrado[
    ot_master_filtrado['estatus'].isin(estados_no_vencidos)
][['ot', 'cliente', 'fecha_entrega', 'estatus', 'fecha_terminado']]

if not ots_completadas_df.empty:
    st.dataframe(ots_completadas_df, use_container_width=True, height=200)
    st.caption(f"Total OTs completadas: {len(ots_completadas_df)}")
else:
    st.info("No hay OTs completadas con los filtros actuales")

# MOVIDO: REPROCESOS después de OTs Completadas
st.markdown("---")
st.header("🔄 Análisis de Reprocesos")

col1, col2 = st.columns(2)

with col1:
    # Gráfico de reprocesos
    if total_ots > 0 and total_reprocesos > 0:
        fig_reprocesos = px.pie(
            values=[total_reprocesos, total_ots - total_reprocesos],
            names=['Reprocesos', 'OTs Normales'],
            title="Distribución: OTs Normales vs Reprocesos",
            hole=0.4,
            color=['Reprocesos', 'OTs Normales'],
            color_discrete_map={'Reprocesos': '#FFA15A', 'OTs Normales': '#636EFA'}
        )
        fig_reprocesos.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_reprocesos, use_container_width=True)
    else:
        st.info("No hay reprocesos para mostrar")

with col2:
    st.subheader("Métricas de Reprocesos")
    st.metric("Total Reprocesos", total_reprocesos)
    st.metric("OTs Normales", total_ots - total_reprocesos)
    st.metric("% Reprocesos", f"{porcentaje_reprocesos:.1f}%")
    
    if total_reprocesos > 0:
        st.warning(f"""
        **Análisis de Reprocesos:**
        - Reprocesos identificados: {total_reprocesos}
        - Tasa de reprocesos: {porcentaje_reprocesos:.1f}%
        - OTs sin problemas: {total_ots - total_reprocesos}
        """)
    else:
        st.success("✅ No se han identificado reprocesos")

# Detalle de reprocesos
if total_reprocesos > 0 and 'es_reproceso' in ot_master_filtrado.columns:
    st.subheader("📋 Detalle de Reprocesos (OTs con Garantía)")
    reprocesos_detalle = ot_master_filtrado[ot_master_filtrado['es_reproceso'] == True][['ot', 'cliente', 'orden_compra', 'estatus']]
    st.dataframe(reprocesos_detalle, use_container_width=True, height=200)

# Gráficos existentes
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 OTs por Cliente")
    if not ot_master_filtrado.empty and 'cliente' in ot_master_filtrado.columns:
        ots_por_cliente = ot_master_filtrado['cliente'].value_counts()
        if not ots_por_cliente.empty:
            fig = px.pie(
                values=ots_por_cliente.values,
                names=ots_por_cliente.index,
                title="Distribución de OTs por Cliente"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de clientes para mostrar")
    else:
        st.info("No hay datos para mostrar")

with col2:
    st.subheader("🎯 OTs por Estatus")
    if not ot_master_filtrado.empty and 'estatus' in ot_master_filtrado.columns:
        ots_por_estatus = ot_master_filtrado['estatus'].value_counts()
        if not ots_por_estatus.empty:
            fig = px.bar(
                x=ots_por_estatus.index,
                y=ots_por_estatus.values,
                title="OTs por Estado",
                labels={'x': 'Estatus', 'y': 'Cantidad'},
                color=ots_por_estatus.index
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de estatus para mostrar")
    else:
        st.info("No hay datos para mostrar")

# Gráfico de procesos
st.subheader("🔧 Procesos más Comunes")

if not procesos_filtrados.empty:
    posibles_nombres = ['proceso', 'Proceso', 'PROCESO', 'proceso_nombre', 'Proceso_Nombre']
    columna_proceso = None
    
    for nombre in posibles_nombres:
        if nombre in procesos_filtrados.columns:
            columna_proceso = nombre
            break
    
    if columna_proceso and not procesos_filtrados[columna_proceso].empty:
        procesos_count = procesos_filtrados[columna_proceso].value_counts().head(10)
        if not procesos_count.empty:
            fig = px.bar(
                x=procesos_count.values,
                y=procesos_count.index,
                orientation='h',
                title="Top 10 Procesos más Frecuentes",
                labels={'x': 'Frecuencia', 'y': 'Proceso'},
                color=procesos_count.values
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de procesos para mostrar")
    else:
        st.info("No se encontró la columna de procesos")
else:
    st.info("No hay datos de procesos para mostrar")

# Horas Estimadas vs Horas Reales
st.subheader("⏰ Horas Estimadas vs Horas Reales por Proceso")

if not procesos_filtrados.empty and 'horas_reales' in procesos_filtrados.columns:
    posibles_nombres = ['proceso', 'Proceso', 'PROCESO', 'proceso_nombre', 'Proceso_Nombre']
    columna_proceso = None
    
    for nombre in posibles_nombres:
        if nombre in procesos_filtrados.columns:
            columna_proceso = nombre
            break
    
    if columna_proceso:
        horas_por_proceso = procesos_filtrados.groupby(columna_proceso).agg({
            'horas_estimadas': 'sum',
            'horas_reales': 'sum'
        }).reset_index()

        if not horas_por_proceso.empty:
            top_procesos = horas_por_proceso.nlargest(10, 'horas_estimadas')

            fig = go.Figure()

            fig.add_trace(go.Bar(
                name='Horas Estimadas',
                x=top_procesos[columna_proceso],
                y=top_procesos['horas_estimadas'],
                marker_color='#1f77b4',
                text=top_procesos['horas_estimadas'].round(1),
                textposition='outside'
            ))

            fig.add_trace(go.Bar(
                name='Horas Reales',
                x=top_procesos[columna_proceso],
                y=top_procesos['horas_reales'],
                marker_color='#ff7f0e',
                text=top_procesos['horas_reales'].round(1),
                textposition='outside'
            ))

            fig.update_layout(
                title="Comparación: Horas Estimadas vs Reales por Proceso",
                xaxis_title="Proceso",
                yaxis_title="Horas",
                barmode='group',
                height=500,
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)

            # Métricas de eficiencia
            st.subheader("📊 Eficiencia en Horas")
            
            total_horas_estimadas = procesos_filtrados['horas_estimadas'].sum()
            total_horas_reales = procesos_filtrados['horas_reales'].sum()
            
            if total_horas_estimadas > 0:
                eficiencia_global = (total_horas_estimadas / total_horas_reales * 100).round(1)
                diferencia_horas = total_horas_reales - total_horas_estimadas
            else:
                eficiencia_global = 0
                diferencia_horas = 0
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Horas Estimadas Totales", f"{total_horas_estimadas:.1f}")
            
            with col2:
                st.metric("Horas Reales Totales", f"{total_horas_reales:.1f}")
            
            with col3:
                st.metric("Diferencia", f"{diferencia_horas:.1f}")
            
            with col4:
                st.metric("Eficiencia", f"{eficiencia_global}%")
        else:
            st.info("No hay datos de horas para mostrar")
    else:
        st.info("No se encontró la columna de procesos")
else:
    st.info("No hay datos de horas reales disponibles")

# NUEVO: GRÁFICO DE DESVIACIONES DE HORAS
st.markdown("---")
st.header("📊 Desviaciones de Horas Programadas")

if total_horas_programadas > 0:
    # Crear datos para el gráfico
    categorias = ['Horas Programadas', 'Desviaciones Positivas', 'Desviaciones Negativas']
    valores = [total_horas_programadas, horas_desviacion_positiva, horas_desviacion_negativa]
    colores = ['#1f77b4', '#2ca02c', '#d62728']
    
    # Gráfico de barras verticales
    fig_desviaciones = go.Figure()
    
    fig_desviaciones.add_trace(go.Bar(
        x=categorias,
        y=valores,
        marker_color=colores,
        text=[f'{val:.1f}h' for val in valores],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Horas: %{y:.1f}<extra></extra>'
    ))
    
    fig_desviaciones.update_layout(
        title="Comparación de Horas Programadas vs Desviaciones",
        yaxis_title="Horas",
        xaxis_title="",
        showlegend=False,
        height=500
    )
    
    st.plotly_chart(fig_desviaciones, use_container_width=True)
    
    # Métricas de desviaciones
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Horas Programadas", f"{total_horas_programadas:.1f}h")
    
    with col2:
        st.metric("Desviaciones Positivas", 
                 f"{horas_desviacion_positiva:.1f}h", 
                 f"{porcentaje_positivo:.1f}%")
    
    with col3:
        st.metric("Desviaciones Negativas", 
                 f"{horas_desviacion_negativa:.1f}h", 
                 f"{porcentaje_negativo:.1f}%",
                 delta_color="inverse")
    
    # Explicación
    st.info("""
    **Explicación de las Desviaciones:**
    - **Horas Programadas**: Total de horas estimadas para todas las OTs
    - **Desviaciones Positivas**: OTs que se completaron dentro o por debajo del tiempo programado
    - **Desviaciones Negativas**: OTs que excedieron el tiempo programado
    """)
else:
    st.warning("No hay datos suficientes de horas para mostrar las desviaciones")

# MOVIDO: GRÁFICO DE FACTURACIÓN al final
st.markdown("---")
st.header("💰 Porcentaje de Facturación")

col1, col2 = st.columns(2)

with col1:
    # Gráfico de dona para facturación
    if total_ots > 0:
        fig_facturacion = px.pie(
            values=[ots_facturadas, total_ots - ots_facturadas],
            names=['Facturado', 'No Facturado'],
            title="Total de OTs vs Facturado",
            hole=0.4,
            color=['Facturado', 'No Facturado'],
            color_discrete_map={'Facturado': '#00CC96', 'No Facturado': '#EF553B'}
        )
        fig_facturacion.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_facturacion, use_container_width=True)
    else:
        st.info("No hay OTs para mostrar el gráfico de facturación")

with col2:
    # Métricas detalladas de facturación
    st.subheader("Detalle de Facturación")
    st.metric("OTs Facturadas", ots_facturadas)
    st.metric("OTs Pendientes", total_ots - ots_facturadas)
    st.metric("Porcentaje de Facturación", f"{porcentaje_facturado:.1f}%")
    
    if total_ots > 0:
        st.info(f"""
        **Resumen de Facturación:**
        - Total OTs: {total_ots}
        - Facturadas: {ots_facturadas}
        - Pendientes: {total_ots - ots_facturadas}
        - Eficiencia: {porcentaje_facturado:.1f}%
        """)
    else:
        st.info("No hay OTs para mostrar el resumen de facturación")

# Tablas de datos
st.markdown("---")
st.header("📋 Datos Detallados")

tab1, tab2 = st.tabs(["OT Master", "Procesos"])

with tab1:
    st.subheader("Tabla OT Master")
    columnas_mostrar = ['ot', 'descripcion', 'cliente', 'estatus', 'fecha_entrega', 'horas_estimadas_ot', 'horas_reales_ot']
    columnas_disponibles = [col for col in columnas_mostrar if col in ot_master_filtrado.columns]
    
    if not ot_master_filtrado.empty:
        st.dataframe(
            ot_master_filtrado[columnas_disponibles],
            use_container_width=True,
            hide_index=True
        )
        
        csv_ot = ot_master_filtrado.to_csv(index=False)
        st.download_button(
            label="📥 Descargar OT Master como CSV",
            data=csv_ot,
            file_name="ot_master_filtrado.csv",
            mime="text/csv"
        )
    else:
        st.info("No hay datos para mostrar en OT Master")

with tab2:
    st.subheader("Tabla Procesos")
    posibles_nombres = ['proceso', 'Proceso', 'PROCESO', 'proceso_nombre', 'Proceso_Nombre']
    columna_proceso = None
    
    for nombre in posibles_nombres:
        if nombre in procesos_filtrados.columns:
            columna_proceso = nombre
            break
    
    columnas_mostrar_procesos = ['ot', columna_proceso, 'horas_estimadas', 'horas_reales', 'empleado_1', 'empleado_2']
    columnas_disponibles_procesos = [col for col in columnas_mostrar_procesos if col in procesos_filtrados.columns]
    
    if not procesos_filtrados.empty:
        st.dataframe(
            procesos_filtrados[columnas_disponibles_procesos],
            use_container_width=True,
            hide_index=True
        )
        
        csv_procesos = procesos_filtrados.to_csv(index=False)
        st.download_button(
            label="📥 Descargar Procesos como CSV",
            data=csv_procesos,
            file_name="procesos_filtrados.csv",
            mime="text/csv"
        )
    else:
        st.info("No hay datos para mostrar en Procesos")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Dashboard de Producción - Adimatec | Desarrollado con Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)
