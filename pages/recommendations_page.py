import streamlit as st
from services import recommendations
from services import products as product_service
from services.ui import token, product_card, error_message


def render():
    st.title('Escolhidos para você')
    st.write('Descubra produtos comprados por clientes com interesses semelhantes aos seus.')
    try:
        auth = token()
        # A avaliação continua disponível mesmo se a consulta de recomendações falhar.
        with st.expander('Avaliar um produto', expanded=True):
            products, _ = product_service.list_products()
            if products:
                with st.form('rating'):
                    product = st.selectbox('Produto', products, format_func=lambda x: x['nome'])
                    rating = st.slider('Sua nota', 1, 5, 5)
                    if st.form_submit_button('Salvar avaliação'):
                        recommendations.rate(auth, product['_id'], rating)
                        st.success('Avaliação salva no grafo.')
        matches = recommendations.recommend(auth)
        if not matches:
            st.info('Ainda não há sugestões para este perfil. Avalie produtos ou realize compras para criar conexões.')
        columns = st.columns(3)
        for index, match in enumerate(matches):
            with columns[index % 3]:
                st.caption(f"{match['clientes_similares']} cliente(s) com interesse em {', '.join(match['interesses_comuns'])}.")
                product_card(product_service.get_product(match['produto_id']), 'recommend')
    except Exception as error:
        error_message(error)
