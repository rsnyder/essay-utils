import axios from 'axios'

export const api = axios.create({
  baseURL: 'https://23jz6yb4ci.execute-api.us-east-1.amazonaws.com/prod'
})

export function get_entity(qid) {
    return api.get(`/entity/${qid}`).then(resp => resp.data)
}