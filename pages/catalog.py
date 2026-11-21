import streamlit as st
from services import products as product_service
from services.ui import product_card, error_message


def render():
    st.title('Encontre seu próximo favorito')
    st.write('Eletrônicos para trabalhar, criar e aproveitar cada momento.')
    try:
        left, right = st.columns([2, 1])
        search = left.text_input('Buscar produto', placeholder='Digite o nome do produto…', max_chars=100)
        category = right.selectbox('Categoria', ['Todas'] + product_service.categories())
        products, source = product_service.list_products(search, category)
        st.caption(f'{len(products)} produtos encontrados · Consulta: {source}')
        if not products:
            st.info('Nenhum produto encontrado. Ajuste a busca ou inicialize os dados.')
        columns = st.columns(3)
        for index, product in enumerate(products):
            with columns[index % 3]:
                product_card(product)
    except Exception as error:
        error_message(error)
