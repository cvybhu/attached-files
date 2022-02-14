#include <variant>
#include <iostream>
#include <cassert>
#include <vector>

struct A {
    int i;
};

struct B {
    std::vector<int> vec;
};

class expression final {
public:
    std::variant<A, B> v;

    expression(std::variant<A, B>&& val) : v(val) {}
};

template <typename Func>
concept invocable_on_const_expression_ref
        = std::invocable<Func, const A&>
        && std::invocable<Func, const B&>;

template <typename Func>
concept invocable_on_expression_ref
        = std::invocable<Func, A&>
        && std::invocable<Func, B&>;

template <typename Func>
concept invocable_on_expression_double_ref
        = std::invocable<Func, A&&>
        && std::invocable<Func, B&&>;

namespace bad {
    auto visit(invocable_on_const_expression_ref auto&& visitor, const expression& e) {
        return std::visit(visitor, e.v);
    }

    auto visit(invocable_on_expression_ref auto&& visitor, expression& e) {
        return std::visit(visitor, e.v);
    }
}

namespace good {
    template <invocable_on_const_expression_ref Visitor>
    std::invoke_result_t<Visitor, const A&> visit(Visitor&& visitor, const expression& e) {
        return std::visit(std::forward<Visitor>(visitor), e.v);
    }

    template <invocable_on_expression_ref Visitor>
    std::invoke_result_t<Visitor, A&> visit(Visitor&& visitor, expression& e) {
        return std::visit(std::forward<Visitor>(visitor), e.v);
    }

    template <invocable_on_expression_double_ref Visitor>
    std::invoke_result_t<Visitor, A&&> visit(Visitor&& visitor, expression&& e) {
        return std::visit(std::forward<Visitor>(visitor), std::move(e.v));
    }
}

namespace doesntwork {
    template <class RetType, class Visitor, class Variant>
    RetType visit(Visitor&& visitor, Variant&& variant) {
        return std::visit(std::forward<Visitor>(visitor), std::forward(variant).v);
    }
}

void visit_const_ref_test() {
    const expression e = expression(A{.i = 4});
    struct {
        const A& operator()(const A& a) {return a;}
        const A& operator()(const B&) {throw "unreachable";}
    } visitor;

    const A& std_res = std::visit(visitor, e.v);
    const A& expr_res = good::visit(visitor, e);

    assert(&std_res == &expr_res);
}

void visit_ref_test() {
    expression e = expression(A{.i = 8});
    struct {
        A& operator()(A& a) {return a;}
        A& operator()(B&) {throw "unreachable";}
    } visitor;

    A& std_res = std::visit(visitor, e.v);
    A& expr_res = good::visit(visitor, e);

    assert(&std_res == &expr_res);
}

void visit_double_ref_test() {
    std::vector<int> one23 = {1, 2, 3};

    expression e1 = expression(B{.vec = one23});
    struct {
        std::vector<int> operator()(A&&) { throw "unreachable"; }
        std::vector<int> operator()(B&& b) { return std::move(b.vec); }
    } visitor;
    
    assert(std::get<B>(e1.v).vec == one23);
    assert(std::visit(visitor, std::move(e1.v)) == one23);
    assert(std::get<B>(e1.v).vec.empty());

    expression e2 = expression(B{.vec = one23});
    assert(std::get<B>(e2.v).vec == one23);
    assert(good::visit(visitor, std::move(e2)) == one23);
    assert(std::get<B>(e2.v).vec.empty());
}

int main() {
    visit_const_ref_test();
    visit_ref_test();
    visit_double_ref_test();
    return 0;
}