"""
    Single qbits and their gates
"""
from sympy import Expr, sympify, Add, Mul, Pow, I, Function, Integer, S, sympify, Matrix, elementary
from sympy.core.numbers import *
from sympy.core.basic import S, sympify
from sympy.core.function import Function
from sympy.functions.elementary.exponential import *
from sympy.functions.elementary.miscellaneous import *
from sympy.matrices.matrices import *
from sympy.simplify import *
from sympy.core.symbol import *

class Qbit(Expr):
    """
    Represents a single quantum gate    
    """
    def __new__(cls, *args):
        for element in args:
            if not (element == 1 or element == 0):
                raise Exception("Values must be either one or zero")
        obj = Expr.__new__(cls, *args, commutative = False)
        return obj

    @property
    def dimension(self):
        return len(self.args)

    def __len__(self):
        return self.dimension

    def __getitem__(self, bit):
        if bit > self.dimension - 1:
            raise Exception()
        return self.args[self.dimension-bit-1]

    def _sympystr(self, printer, *args):
        string = ""
        for it in self.args:
            string = string + str(it)
        return "|%s>" % printer._print(string, *args)

    def _sympyrepr(self, printer, *args):
        return "%s%s" % (printer._print(self.__class__.__name__, *args), printer._print(str(self.args)))

    def flip(self, *args):
        newargs = list(self.args[:])
        for i in args:
            if newargs[self.dimension-i-1] == 1:
                newargs[self.dimension-i-1] = 0
            else:
                newargs[self.dimension-i-1] = 1
        return Qbit(*newargs)

    def _represent_ZBasisSet(self):
        n = 1
        definiteState = 0
        for it in reversed(self.args):
            definiteState += n*it
            n = n*2
        result = [0 for x in range(2**self.dimension)]
        result[definiteState] = 1

        return Matrix(result)

    def _represent_XBasisSet(self):
        return basisChangeState(self._represent_ZBasisSet(), self.XBasisTransform)            

    def _represent_YBasisSet(self):
        return basisChangeState(self._represent_ZBasisSet(), self.YBasisTransform) 

    @property
    def XBasisTransform(self):
        return 1/sqrt(2)*Matrix([[1,1],[1,-1]])

    @property
    def YBasisTransform(self):
        return Matrix([[ImaginaryUnit(),0],[0,-ImaginaryUnit()]])

class Gate(Expr):
    """
    A gate operator that acts on qubit(s)
    (will need tensor product to get it working for multiple Qbits)
    """
    def __new__(cls, *args):
        obj = Expr.__new__(cls, *args, commutative = False)
        if obj.inputnumber != len(args):
            num = obj.inputnumber
            raise Exception("This gate applies to %d qbits" % (num))
        for i in range(len(args)):
            if args[i] in (args[:i] + args[i+1:]):
                raise Exception("Can't have duplicate control and target bits!")
        return obj

    @property
    def matrix(self):
        raise NotImplementedError("matrixRep Not implemented")
        
    @property
    def minimumdimension(self):
        return max(self.args)
        
    @property
    def inputnumber(self):
        mat = self.matrix
        return log((mat).cols,2)
        
    def _apply(self, qbits, mat):
        assert isinstance(qbits, Qbit), "can only apply self to qbits"
        # check number of qbits this gate acts on
        if self.minimumdimension >= qbits.dimension:
            raise HilbertSpaceException()    
        if isinstance(qbits, Qbit):
            #find which column of the matrix this qbit applies to 
            args = [self.args[i] for i in reversed(range(len(self.args)))]
            column_index = 0
            n = 1
            for element in args:
                column_index += n*qbits[element]
                n = n<<1
            column = mat[:,column_index]
            #now apply each column element to qbit
            result = 0
            for index in range(len(column.tolist())):
                new_qbit = Qbit(*qbits.args)
                for bit in range(len(args)):
                    if new_qbit[args[bit]] != (index>>bit)&1:
                        new_qbit = new_qbit.flip(args[bit])
                result += column[index]*new_qbit
        else:
            raise Exception("can't apply to object that is not a qbit")
        return result        

    def _apply_ZBasisSet(self, qbits):
        #switch qbit basis and matrix basis when fully implemented
        mat = self.matrix
        return self._apply(qbits, mat)        


    def _sympyrepr(self, printer, *args):
        return "%s(%s)" %  (printer._print(self.__class__.__name__, *args), printer._print(self.args, *args))

    def _represent_ZBasisSet(self, HilbertSize, format = 'sympy'):
        if self.minimumdimension >= HilbertSize:
            raise HilbertSpaceException()
        gate = self.matrix
        if HilbertSize  == 1:            
            return gate
        else:
            m = representHilbertSpace(gate, HilbertSize, self.args, format)
            return m 

    def _represent_XBasisSet(self, HilbertSize):
        if self.minimumdimension >= HilbertSize:
            raise HilbertSpaceException()
        gate = basisChangeOperator(self.matrix, self.XBasisTransform)
        if HilbertSize  == 1:            
            return gate
        else:
            m = representHilbertSpace(gate, HilbertSize, self.args)
            return m

    def _represent_YBasisSet(self, HilbertSize):
        raise NotImplementedError("Y-Basis Representation not implemented")

    @property
    def XBasisTransform(self):
        return 1/sqrt(2)*Matrix([[1,1],[1,-1]])

    @property
    def YBasisTransform(self):
        return Matrix([[ImaginaryUnit(),0],[0,-ImaginaryUnit()]])

def representHilbertSpace(gateMatrix, HilbertSize, qbits, format='sympy'):

    #returns |first><second|, if first and second are 0 or 1.    
    def _operator(first, second, format):
        if (first != 1 and first != 0) or (second != 1 and second != 0):
            raise Exception("can only make matricies |0><0|, |1><1|, |0><1|, or |1><0|")
        if first:
            if second:
                ret = Matrix([[0,0],[0,1]])
            else:
                ret = Matrix([[0,0],[1,0]])
        else:
            if second:
                ret = Matrix([[0,1],[0,0]])
            else:
                ret = Matrix([[1,0],[0,0]])
        if format == 'sympy':
            return ret
        else:
            import numpy as np
            return np.matrix(ret.tolist())

    #Wrapper function that gives np.kron same interface as TensorProduct
    def npTensorProduct(*product):
        answer = product[0]
        for item in product[1:]:
            answer = np.kron(answer, item)
        return answer

    if format == 'sympy':
        eye = getattr(gateMatrix, 'eye')
        kron = TensorProduct
    elif format=='numpy':
        #if user specified numpy as matrix format, try to import
        try:         
            import numpy as np
        except Exception:
            #If we couldn't load, just revert to sympy
            representHilbertSpace(gateMatrix, HilbertSize, qbits, format ='sympy')
        #redirect eye to the numpy eye function, and kron to a modified numpy function
        gateMatrix = np.matrix(gateMatrix.tolist())
        aeye = getattr(np, 'eye')
        eye = lambda x: np.matrix(aeye(x))
        kron = npTensorProduct      
    else:
        raise ValueError()

    if gateMatrix.shape[1] == 2:
        product = []
        qbit = qbits[0]
        #fill product with [I1,Gate,I2] such that the unitaries, I, cause the gate to be applied to the correct qbit  
        if qbit != HilbertSize-1:
            product.append(eye(2**(HilbertSize-qbit-1)))    
        product.append(gateMatrix)
        if qbit != 0:
            product.append(eye(2**qbit))

        #do the tensor product of these I's and gates
        if format == 'sympy' or format == 'numpy':
            MatrixRep = kron(*product)
        else:
            raise ValueError()         
        return MatrixRep

    #If we are dealing with a matrix that is inheritely multi-qubit, do more work
    else:
        #find the control and target qbit(s)
        controls = qbits[:-1]
        controls = [x for x in reversed(controls)]
        target =  qbits[-1]
        answer = 0
        product = []
        #break up gateMatrix into list of 2x2 matricies's
        #This list will be used for determining what matrix goes where
        matrixArray = []
        for i in range(gateMatrix.shape[1]/2):
            for j in range(gateMatrix.shape[1]/2):
                matrixArray.append(gateMatrix[i*2:i*2+2,j*2:j*2+2])

        #Build up tensor products and additions, so that we can form matrix
        for i in range((gateMatrix.shape[1]/2)**2):
            product = []
            #Put Unities in all locations
            for j in range(HilbertSize):
                product.append(eye(2))
            n = 0
            #put Operators |0><0|, |1><1|, |0><1|, or |1><0| in place of I's for control bits
            for item in controls:
                product.pop(HilbertSize-1-item)
                product.insert(HilbertSize-1-item, _operator(i>>(n+len(controls))&1,(i>>n)&1, format))
                n = n+1
            #put the correct submatrix from matrixarray into target-bit location
            product.pop(HilbertSize-1-target)
            product.insert(HilbertSize-1-target, matrixArray[i])

            #preform Tensor product first time
            if isinstance(answer, (int, Integer)):
                if format == 'sympy' or format == 'numpy':
                    answer = kron(*product)
                else:
                    raise ValueError()
            #add last answer to TensorProduct of what we have
            else:
                if format == 'sympy' or format == 'numpy':
                    answer = answer + kron(*product)
                else:
                    raise ValueError()
        return answer
          
def TensorProduct(*args):
    #pull out the first element in the product
    MatrixExpansion  = args[len(args)-1]

    #do the tensor product working from right to left
    for gate in reversed(args[:len(args)-1]):
        rows = gate.rows
        cols = gate.cols 
        #go through each row appending tensor product to running MatrixExpansion      
        for i in range(rows): 
            Start = MatrixExpansion*gate[i*cols]                       
            #go through each column joining each item
            for j in range(cols-1):
                Start = Start.row_join(MatrixExpansion*gate[i*cols+j+1])
            #if this is the first element in row, make it the start of the new row 
            if i == 0:
                Next = Start
            else:
                Next = Next.col_join(Start)
        MatrixExpansion = Next
    return MatrixExpansion

class BasisSet(Expr):
    pass

class ZBasisSet(BasisSet):
    pass

class XBasisSet(BasisSet):
    pass

class YBasisSet(BasisSet):
    pass

class CZGate(Gate):
    @property
    def matrix(self):
        return Matrix([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,-1]])

class SwapGate(Gate):
    @property
    def matrix(self):
        return Matrix([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]])

class CPhaseGate(Gate):
    @property
    def matrix(self):
        return Matrix([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1*ImaginaryUnit()]])

class ToffoliGate(Gate):
    @property
    def matrix(self):
        return Matrix([[1,0,0,0,0,0,0,0],[0,1,0,0,0,0,0,0],[0,0,1,0,0,0,0,0],[0,0,0,1,0,0,0,0],[0,0,0,0,1,0,0,0],[0,0,0,0,0,1,0,0],[0,0,0,0,0,0,0,1],[0,0,0,0,0,0,1,0]])

class CNOTGate(Gate):
    @property
    def matrix(self):
        return Matrix([[1,0,0,0],[0,1,0,0],[0,0,0,1],[0,0,1,0]])

class HadamardGate(Gate):
    """
    An object representing a Hadamard Gate
    """    
    def _sympystr(self, printer, *args):
        return "H(%s)" % printer._print(self.args[0], *args)

    @property
    def matrix(self):
        return Matrix([[1, 1], [1, -1]])*(1/sqrt(2))
                  
class XGate(Gate):
    """
    An object representing a Pauli-X gate:
    """
    def _sympystr(self, printer, *args):
        return "X(%s)" % printer._print(self.args[0], *args)

    @property
    def matrix(self):
        return Matrix([[0, 1], [1, 0]])

class YGate(Gate):
    """
    An object representing a Pauli-Y gate:
    """
    def _sympystr(self, printer, *args):
        return "Y(%s)" % printer._print(self.args[0], *args)

    @property
    def matrix(self):
        return Matrix([[0, complex(0,-1)], [complex(0,1), 0]])

class ZGate(Gate):
    """
    An object representing a Pauli-Z gate:
    """
    def _sympystr(self, printer, *args):
        return "Z(%s)" % printer._print(self.args[0], *args)

    @property
    def matrix(self):
        return Matrix([[1, 0], [0, -1]])

class PhaseGate(Gate):
    """
    An object representing a phase gate:
    """
    def _sympystr(self, printer, *args):
        return "S(%s)" % printer._print(self.args[0], *args)

    @property
    def matrix(self):
        return Matrix([[1, 0], [0, complex(0,1)]])

class TGate(Gate):
    """
    An object representing a pi/8 gate:
    """
    def _sympystr(self, printer, *args):
        return "T(%s)" % printer._print(self.args[0], *args)

    @property
    def matrix(self):
        return Matrix([[1, 0], [0, exp(I*Pi()/4)]])

def apply_gates(circuit, basis = ZBasisSet()):
    # if all we have is a Qbit without any gates, return
    if isinstance(circuit, Qbit):
        return circuit

    #if we have a Mul object, get the state of the system
    if isinstance(circuit, Mul):
        states = circuit.args[len(circuit.args)-1]
        states = states.expand()

    #if we have an add object with gates mixed in, apply_gates recursively
    if isinstance(circuit, Add):
        result = 0
        for i in circuit.args:
            result = result + apply_gates(i, basis)
        return result        

    state_coeff = 1
    #pick out each object that multiplies the state
    for multiplier in reversed(circuit.args[:len(circuit.args)-1]):
    
        #if the object that mutliplies is a Gate, we will apply it once
        if isinstance(multiplier, Gate):
            gate = multiplier
            number_of_applications = 1
            
        #if the object that multiplies is a Pow who's base is a Gate, we will apply Pow.exp times
        elif isinstance(multiplier, Pow) and isinstance(multiplier.base, Gate):
            gate = multiplier.base
            number_of_applications = multiplier.exp
            
        #if the object that multiplies is not a gate of any sort, we apply it by multiplying
        else:
            state_coeff = multiplier*state_coeff
            continue

        #if states is in superposition of states (a sum of qbits states), applyGates to each state contined within
        if isinstance(states, Add):
            result = 0            
            for state in states.args:
                result = result + apply_gates(gate**number_of_applications*state, basis)
            states = result
            states = states.expand()

        #if we have a mul, apply gate to each register and multiply result
        elif isinstance(states, Mul):
            #find the Qbits in the Mul
            states = Mul(*states.args)
            for i in range(len(states.args)):
                if isinstance(states.args[i],Qbit):
                    break
            #if we didn't find one, something is wrong
            if not isinstance(states.args[i],Qbit):
                print states
                raise Exception()
 
            #apply the gate the right number of times to this state
            coefficient = Mul(*(states.args[:i]+states.args[i+1:]))
            states = apply_gates(gate**(number_of_applications)*states.args[i], basis)
            states = coefficient*states            
            states = states.expand()
            
        #If we have a single Qbit, apply to this Qbit
        elif isinstance(states, Qbit):
            basis_name = basis.__class__.__name__
            apply_method_name = '_apply_%s' % basis_name  
            apply_method = getattr(gate, apply_method_name)
            states = apply_method(states)
            states = states.expand()
            number_of_applications -= 1
            while number_of_applications > 0:
                states = apply_gates(gate*states)
                number_of_applications -= 1
       
        #if it's not one of those, there is something wrong
        else:
            raise Exception()

    #tack on any coefficients that were there before and simplify
    states = state_coeff*states
    if isinstance(states, (Mul,Add,Pow)):
        states = states.expand()
    return states
             
    
"""
# Look at dimension of basis, only work if it is not a symbol, the dispatch to Qbits._represent_BasisClass
Qbits.represent(self, basis):  
Qbits._represent_XBasisSet(self, dimension):
Qbits._represent_YBasisSet(self, dimension):
"""

def matrix_to_qbits(matrix):
    #make sure it is of correct dimensions for a qbit-matrix representation
    qbit_number = log(matrix.rows,2)
    if matrix.cols != 1 or not isinstance(qbit_number, Integer):
        raise Exception()

    #go through each item in matrix, if element is not zero, make it into a qbit item times coefficient
    result = 0
    mlistlen = len(matrix.tolist())
    for i in range(mlistlen):
        if matrix[i] != 0:
            #form qbit array; 0 in bit-locations where i is 0, 1 in bit-locations where i is 1
            qbit_array = [1 if i&(1<<x) else 0 for x in range(qbit_number)]
            qbit_array.reverse()  
            result = result + matrix[i]*Qbit(*qbit_array)
            
    #if sympy simplified by pulling out a constant coefficient, undo that
    if isinstance(result, (Mul,Add,Pow)):
        result = result.expand()
    return result

def qbits_to_matrix(qbits):
    #get rid of multiplicative constants
    qbits = qbits.expand()
    
    #if we have a Mul object, find the qbit part qbits to matrix it
    if isinstance(qbits, Mul):
        for i in range(len(qbits.args)):
            if isinstance(qbits.args[i], Qbit):
                break
        if not isinstance(qbits.args[i], Qbit):
            raise Exception()
        #recursively turn qbit into matrix
        return Mul(*(qbits.args[:i] + qbits.args[i+1:]))*qbits_to_matrix(qbits.args[i]) 
    #recursively turn each item in an add into a matrix
    elif isinstance(qbits, Add):
        result = qbits_to_matrix(qbits.args[0])
        for element in qbits.args[1:]:
            result = result + qbits_to_matrix(element)
        return result
    #if we are at the bottom of the recursion, have the base case be representing the matrix
    elif isinstance(qbits, Qbit):
        return qbits._represent_ZBasis() #TODO other bases with getattr
    else:
        raise Exception("Malformed input")

def represent(circuit, basis = ZBasisSet(), GateRep = False, HilbertSize = None, format = 'sympy'):
    """
        Represents the elements in a certain basis 
    """
    basis_name = basis.__class__.__name__
    rep_method_name = '_represent_%s' % basis_name

    circuit = circuit.expand()
    # check if the last element in circuit is Gate
    # if not raise exception becuase size of Hilbert space undefined
    if isinstance(circuit, Qbit):
        return getattr(circuit, rep_method_name)()
    elif isinstance(circuit, Gate):
        if HilbertSize == None:
            raise HilbertSpaceException("User must specify HilbertSize when gates are not applied on Qbits") 
        gate = circuit
        rep_method = getattr(gate, rep_method_name)
        gate_rep = rep_method(HilbertSize, format)
        return gate_rep
    elif isinstance(circuit, Add):
        out = 0
        for i in circuit.args:
            if not out:
                out = represent(i, basis, GateRep, HilbertSize, format)
            else:
                out = out + represent(i, basis, GateRep, HilbertSize, format)
        return out
    elif not isinstance(circuit, Mul):
        raise Exception("Malformed input")

    qbit = circuit.args[len(circuit.args)-1]
    if isinstance(qbit, Qbit):
        HilbertSize = len(qbit)
        #Turn the definite state of Qbits |X> into a single one in the Xth element of its column vector
        result = getattr(qbit, rep_method_name)()
    elif HilbertSize == None:    
        raise HilbertSpaceException("User must specify HilbertSize when gates are not applied on Qbits")        
    else:
        gate = qbit
        rep_method = getattr(gate, rep_method_name)
        gate_rep = rep_method(HilbertSize, format)
        result = gate_rep


    #go through each gate (from left->right) and apply it in X basis
    for gate in reversed(circuit.args[:len(circuit.args)-1]):
        basis_name = basis.__class__.__name__
        rep_method_name = '_represent_%s' % basis_name
        if isinstance(gate, Pow) and isinstance(gate.base, Gate):
            number_of_applications = gate.exp
            gate = gate.base
            rep_method = getattr(gate, rep_method_name)
            gate_rep = rep_method(HilbertSize, format)
            for i in range(number_of_applications):
                result = gate_rep*result
        elif hasattr(gate,  rep_method_name):
            rep_method = getattr(gate, rep_method_name)
            gate_rep = rep_method(HilbertSize, format)
            result = gate_rep*result
        else:
            result = gate*result

    return result


def gatesimp(circuit):
    """ will simplify gates symbolically"""
    #Pull gates out of inner Add's and Mul's?

    #bubble sort(?) out gates that commute
    circuit = gatesort(circuit)
    
    #do simplifications
    if isinstance(circuit, Mul):
        for i in range(len(circuit.args)):
            #H,X,Y or Z squared is 1. T**2 = S, S**2 = Z 
            if isinstance(circuit.args[i], Pow):
                if isinstance(circuit.args[i].base, (HadamardGate, XGate, YGate, ZGate)) and isinstance(circuit.args[i].exp, Integer):
                    newargs = (circuit.args[:i] + (circuit.args[i].base**(circuit.args[i].exp % 2),) + circuit.args[i+1:])
                    circuit = gatesimp(Mul(*newargs))
                    break
                elif isinstance(circuit.args[i].base, PhaseGate):
                    newargs = (circuit.args[:i] + (ZGate(circuit.args[i].base.args[0])**(Integer(circuit.args[i].exp/2)), circuit.args[i].base**(circuit.args[i].exp % 2)) + circuit.args[i+1:])
                    circuit =  gatesimp(Mul(*newargs))
                    break
                elif isinstance(circuit.args[i].base,TGate):
                    newargs = (circuit.args[:i] + (SGate(circuit.args[i].base.args[0])**Integer(circuit.args[i].exp/2), circuit.args[i].base**(circuit.args[i].exp % 2)) + circuit.args[i+1:])
                    circuit =  gatesimp(Mul(*newargs))
                    break
            #Deal with HXH = Z, HZH = X, HYH = -Y
            if isinstance(circuit.args[i], HadamardGate):
                #check for X,Y,Z in front
                pass
                #check for Hadamard to right of that
                #replace stuff
                
            
    return circuit

def gatesort(circuit):
    #bubble sort of gates checking for commutivity of neighbor (Python doesn't have a do-while)
    changes = True
    while changes:
        changes = False
        cirArray = circuit.args
        for i in range(len(cirArray)-2):
            #Go through each element and switch ones that are in wrong order
            if isinstance(cirArray[i], (Gate, Pow)) and isinstance(cirArray[i+1], (Gate, Pow)):
                if isinstance(cirArray[i], Pow):
                    first = cirArray[i].base
                else:
                    first = cirArray[i]
    
                if isinstance(cirArray[i+1], Pow):
                    second = cirArray[i+1].base
                else:
                    second = cirArray[i+1]
    
                if first.args > second.args:
                    #make sure elements commute, meaning they do not affect ANY of the same qbits
                    commute = True
                    for arg1 in cirArray[i].args:
                       for arg2 in cirArray[i+1].args:
                            if arg1 == arg2:
                                commute = False
                    # if they do commute, switch them
                    if commute:
                        circuit = Mul(*(circuit.args[:i] + (circuit.args[i+1],) + (circuit.args[i],) + circuit.args[i+2:])) 
                        cirArray = circuit.args
                        changes = True
    return circuit    

class HilbertSpaceException(Exception):
    pass

#This doesn't really work yet
def basisChangeOperator(gate, tranmat):
    return tranmat*gate*(Dagger(tranmat))

def basisChangeState(state, tranmat):
    mat = []
    for i in range(log(state.rows,2)):
        mat = mat + [tranmat,]
    tranmat = TensorProduct(*mat)

    return tranmat*state

#This is a Facsimile of Matt's code
class Dagger(Expr):
    """
General hermitian conjugate operation.
"""

    def __new__(cls, arg):
        if isinstance(arg, Matrix):
            return cls.eval(arg)
        arg = sympify(arg)
        r = cls.eval(arg)
        if isinstance(r, Expr):
            return r
        obj = Expr.__new__(cls, arg)
        return obj

    @classmethod
    def eval(cls, arg):
        """
Evaluates the Dagger instance.
"""
        try:
            d = arg._eval_dagger()
        except:
            if isinstance(arg, Expr):
                if arg.is_Add:
                    return Add(*tuple(map(Dagger, arg.args)))
                if arg.is_Mul:
                    return Mul(*tuple(map(Dagger, reversed(arg.args))))
                if arg.is_Number:
                    return arg
                if arg.is_Pow:
                    return Pow(Dagger(arg.args[0]), Dagger(arg.args[1]))
                if arg == I:
                    return -arg
            # transpose and replace each matrix element with complex conjugate
            elif isinstance(arg, Matrix):
                arg = arg.T
                for i in range(arg.rows*arg.cols):
                    arg[i] = Dagger(arg[i])
                return arg
            else:
                return None
        else:
            return d

    def _eval_subs(self, old, new):
        r = Dagger(self.args[0].subs(old, new))
        return r

    def _eval_dagger(self):
        return self.args[0]

