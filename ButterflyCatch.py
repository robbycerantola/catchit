# Author: Ryan Myers
# Models: Jeff Styers, Reagan Heller
# Modified by Robby Cerantola to create a simple game   

# Last Updated: 
#
# This tutorial provides an example of creating a character
# and having it walk around on uneven terrain, as well
# as implementing a fully rotatable camera.

# Modified .........

import direct.directbase.DirectStart
from panda3d.core import CollisionTraverser,CollisionNode
from panda3d.core import CollisionHandlerQueue,CollisionRay
from panda3d.core import Filename,AmbientLight,DirectionalLight
from panda3d.core import PandaNode,NodePath,Camera,TextNode
from panda3d.core import Vec3,Vec4,BitMask32
from direct.gui.OnscreenText import OnscreenText
from direct.actor.Actor import Actor
from direct.showbase.DirectObject import DirectObject
import random, sys, os, math

SPEED = 0.5

# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(1,1,1,1),
                        pos=(-1.3, pos), align=TextNode.ALeft, scale = .05)

# Function to put title on the screen.
def addTitle(text):
    return OnscreenText(text=text, style=1, fg=(1,1,1,1),
                        pos=(1.3,-0.95), align=TextNode.ARight, scale = .07)

class World(DirectObject):

    def __init__(self):
        
        self.keyMap = {"left":0, "right":0, "forward":0, "cam-left":0, "cam-right":0, "grab":0,"jump":0,"run":0,"walk":0}
        base.win.setClearColor(Vec4(0,0,0,1))

        # Post the instructions

        self.title = addTitle("RC-Soft: Catch the butterfly")
        self.inst1 = addInstructions(0.95, "[ESC]: Quit")
        self.inst2 = addInstructions(0.90, "[Left Arrow]: Rotate Ralph Left")
        self.inst3 = addInstructions(0.85, "[Right Arrow]: Rotate Ralph Right")
        self.inst4 = addInstructions(0.80, "[Up Arrow]: Run Ralph Forward")
        self.inst6 = addInstructions(0.70, "[A]: Rotate Camera Left")
        self.inst7 = addInstructions(0.65, "[S]: Rotate Camera Right")
        self.inst8 = addInstructions(0.60,"[G]: Grab")
        self.inst9 = addInstructions(0.55,"[J]: Jump [R]: Run [W]:Walk")
        # Set up the environment
        #
        # This environment model contains collision meshes.  If you look
        # in the egg file, you will see the following:
        #
        #    <Collide> { Polyset keep descend }
        #
        # This tag causes the following mesh to be converted to a collision
        # mesh -- a mesh which is optimized for collision, not rendering.
        # It also keeps the original mesh, so there are now two copies ---
        # one optimized for rendering, one for collisions.  

        self.environ = loader.loadModel("models/world")      
        self.environ.reparentTo(render)
        self.environ.setPos(0,0,0)
        
        # Create the main character, Ralph

        ralphStartPos = self.environ.find("**/start_point").getPos()
        self.ralph = Actor("models/ralph",
                                 {"run":"models/ralph-run",
                                  "walk":"models/ralph-walk",
                                 "grab":"models/ralph-run" })  ## TODO : create model grab action
        self.ralph.reparentTo(render)
        self.ralph.setScale(.2)
        self.ralph.setPos(ralphStartPos)

        #show my fly
        self.fly=Actor("models/fluture",
                                 {"run":"models/fluture-anim1",
                                  "walk":"models/fluture-anim1"}) 
        self.fly.reparentTo(render)
        self.fly.setScale(.08)
        self.fly.setPos(ralphStartPos)
        self.fly.loop("run") #start fly animation


        # Create a floater object.  We use the "floater" as a temporary
        # variable in a variety of calculations.
        
        self.floater = NodePath(PandaNode("floater"))
        self.floater.reparentTo(render)

        # Accept the control keys for movement and rotation

        self.accept("escape", sys.exit)
        self.accept("arrow_left", self.setKey, ["left",1])
        self.accept("arrow_right", self.setKey, ["right",1])
        self.accept("arrow_up", self.setKey, ["forward",1])
        self.accept("a", self.setKey, ["cam-left",1])
        self.accept("s", self.setKey, ["cam-right",1])
        self.accept("arrow_left-up", self.setKey, ["left",0])
        self.accept("arrow_right-up", self.setKey, ["right",0])
        self.accept("arrow_up-up", self.setKey, ["forward",0])
        self.accept("a-up", self.setKey, ["cam-left",0])
        self.accept("s-up", self.setKey, ["cam-right",0])
        self.accept('1', self.setObject, [0])
        self.accept('2', self.setObject, [1])
        self.accept('3', self.setObject, [2])
        self.accept('4', self.setObject, [3])
        self.accept('g' ,self.setKey, ["grab",1])
        self.accept('j', self.setKey,["jump",1])
        self.accept('j-up', self.setKey,["jump",0])
        self.accept('r', self.setKey,["run",1])
        self.accept('w', self.setKey,["walk",1])
        taskMgr.add(self.move,"moveTask")

        # Game state variables
        self.isMoving = False

        # Set up the camera
        
        base.disableMouse()
        base.camera.setPos(self.ralph.getX(),self.ralph.getY()+10,2)
        
        # We will detect the height of the terrain by creating a collision
        # ray and casting it downward toward the terrain.  One ray will
        # start above ralph's head, and the other will start above the camera.
        # A ray may hit the terrain, or it may hit a rock or a tree.  If it
        # hits the terrain, we can detect the height.  If it hits anything
        # else, we rule that the move is illegal.

        self.cTrav = CollisionTraverser()

        self.ralphGroundRay = CollisionRay()
        self.ralphGroundRay.setOrigin(0,0,1000)
        self.ralphGroundRay.setDirection(0,0,-1)
        self.ralphGroundCol = CollisionNode('ralphRay')
        self.ralphGroundCol.addSolid(self.ralphGroundRay)
        self.ralphGroundCol.setFromCollideMask(BitMask32.bit(0))
        self.ralphGroundCol.setIntoCollideMask(BitMask32.allOff())
        self.ralphGroundColNp = self.ralph.attachNewNode(self.ralphGroundCol)
        self.ralphGroundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.ralphGroundColNp, self.ralphGroundHandler)

        self.camGroundRay = CollisionRay()
        self.camGroundRay.setOrigin(0,0,1000)
        self.camGroundRay.setDirection(0,0,-1)
        self.camGroundCol = CollisionNode('camRay')
        self.camGroundCol.addSolid(self.camGroundRay)
        self.camGroundCol.setFromCollideMask(BitMask32.bit(0))
        self.camGroundCol.setIntoCollideMask(BitMask32.allOff())
        self.camGroundColNp = base.camera.attachNewNode(self.camGroundCol)
        self.camGroundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.camGroundColNp, self.camGroundHandler)

        # Uncomment this line to see the collision rays
        #self.ralphGroundColNp.show()
        #self.camGroundColNp.show()
       
        # Uncomment this line to show a visual representation of the 
        # collisions occuring
        #self.cTrav.showCollisions(render)
        
        # Create some lighting
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor(Vec4(.3, .3, .3, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection(Vec3(-5, -5, -5))
        directionalLight.setColor(Vec4(1, 1, 1, 1))
        directionalLight.setSpecularColor(Vec4(1, 1, 1, 1))
        render.setLight(render.attachNewNode(ambientLight))
        render.setLight(render.attachNewNode(directionalLight))
    
    # show an object in Ralph's hand
            #Now we will expose the joint the hand joint. ExposeJoint allows us to
        #get the position of a joint while it is animating. This is different than
        #controlJonit which stops that joint from animating but lets us move it.
        #This is particularly usefull for putting an object (like a weapon) in an
        #actor's hand
        self.rightHand = self.ralph.exposeJoint(None, 'modelRoot', 'RightHand')

        #This is a table with models, positions, rotations, and scales of objects to
        #be attached to our exposed joint. These are stock models and so they needed
        #to be repositioned to look right.
        positions = [("models/net", (0,-.66,-.95), (90,0,90), .4),
                     ("models/fluture", (.15,-.99,-.22), (90,0,90), .5),
                     ("models/banana", (.08,-.1,.09), (0,-90,0), 1.75),
                     ("models/sword", (.11,.19,.06), (0,0,90), 1)]
        self.models = []                 #A list that will store our models objects
        for row in positions:
          np = loader.loadModel(row[0])              #Load the model
          np.setPos(row[1][0], row[1][1], row[1][2]) #Position it
          np.setHpr(row[2][0], row[2][1], row[2][2]) #Rotate it
          np.setScale(row[3])                        #Scale it
          #Reparent the model to the exposed joint. That way when the joint moves,
          #the model we just loaded will move with it.
          np.reparentTo(self.rightHand)
          self.models.append(np)                     #Add it to our models list
        
        self.setObject(0)
        

    
    def setObject(self, i):
        for np in self.models: np.hide()
        self.models[i].show()
    
    #Records the state of the arrow keys
    def setKey(self, key, value):
        self.keyMap[key] = value
    

    # Accepts arrow keys to move either the player or the menu cursor,
    # Also deals with grid checking and collision detection
    def move(self, task):

        # If the camera-left key is pressed, move camera left.
        # If the camera-right key is pressed, move camera right.

        base.camera.lookAt(self.ralph)
        if (self.keyMap["cam-left"]!=0):
            base.camera.setX(base.camera, -20 * globalClock.getDt())
        if (self.keyMap["cam-right"]!=0):
            base.camera.setX(base.camera, +20 * globalClock.getDt())

        # save ralph's initial position so that we can restore it,
        # in case he falls off the map or runs into something.

        startpos = self.ralph.getPos()

        # If a move-key is pressed, move ralph in the specified direction.
        #dmove=150
        #dforw=10
        if (self.keyMap["run"]!=0): #if r key is pressed than run until arrows keys are depressed
            dmove=300               #run means that the change of position has a bigger value
            dforw=25
            #if self.isMoving:
            #    self.ralph.loop("run")
        else:
            dmove=150
            dforw=10
        if (self.keyMap["left"]!=0):
            self.ralph.setH(self.ralph.getH() + dmove * globalClock.getDt())
        if (self.keyMap["right"]!=0):
            self.ralph.setH(self.ralph.getH() - dmove * globalClock.getDt())
        if (self.keyMap["forward"]!=0):
            self.ralph.setY(self.ralph, -dforw * globalClock.getDt())

        # If ralph is moving, loop the run animation.
        # If he is standing still, stop the animation.

        if (self.keyMap["walk"]!=0):
            if self.isMoving:
                self.ralph.loop("walk")
            self.setKey("run",0)
            self.setKey("walk",0)

        if (self.keyMap["forward"]!=0) or (self.keyMap["left"]!=0) or (self.keyMap["right"]!=0):
            if self.isMoving is False:
                if self.keyMap["run"] !=0:
                    self.ralph.loop("run")
                    #self.setKey("run",0)
                else:
                    self.ralph.loop("walk")
                    
                self.isMoving = True
        else:
            if self.isMoving:
                self.ralph.stop()
                self.ralph.pose("walk",5)
                self.isMoving = False
        
        #Jump at different higths depending on velocity
        if(self.keyMap["jump"]!=0):
            if (self.keyMap["run"]!=0):
                jmp=0.4
            else:
                jmp=0.2
        else:
            jmp=0
        # grab something ->activate grab animation
        if(self.keyMap["grab"]!=0):
            if self.isMoving is False:
                
                self.ralph.pose("grab",1)  #workaround untill animation is ready!!
                
            self.keyMap["grab"]=0
        # If the camera is too far from ralph, move it closer.
        # If the camera is too close to ralph, move it farther.

        camvec = self.ralph.getPos() - base.camera.getPos() 
        camvec.setZ(0)
        camdist = camvec.length()
        camvec.normalize()
        if (camdist > 10.0):
            base.camera.setPos(base.camera.getPos() + camvec*(camdist-10))
            camdist = 10.0
        if (camdist < 5.0):
            base.camera.setPos(base.camera.getPos() - camvec*(5-camdist))
            camdist = 5.0

        # Now check for collisions.

        self.cTrav.traverse(render)

        # Adjust ralph's Z coordinate.  If ralph's ray hit terrain,
        # update his Z. If it hit anything else, or didn't hit anything, put
        # him back where he was last frame.

        entries = []
        for i in range(self.ralphGroundHandler.getNumEntries()):
            entry = self.ralphGroundHandler.getEntry(i)
            if entry.getIntoNode().getName()!="terrain":
                print entry
            entries.append(entry)
        entries.sort(lambda x,y: cmp(y.getSurfacePoint(render).getZ(),
                                     x.getSurfacePoint(render).getZ()))
        
        if (len(entries)>0) and (entries[0].getIntoNode().getName() == "terrain"):
            self.ralph.setZ(entries[0].getSurfacePoint(render).getZ()+jmp)
        else:
            self.ralph.setPos(startpos)

        # Keep the camera at one foot above the terrain,
        # or two feet above ralph, whichever is greater.
        
        entries = []
        for i in range(self.camGroundHandler.getNumEntries()):
            entry = self.camGroundHandler.getEntry(i)
            entries.append(entry)
        entries.sort(lambda x,y: cmp(y.getSurfacePoint(render).getZ(),
                                     x.getSurfacePoint(render).getZ()))
        if (len(entries)>0) and (entries[0].getIntoNode().getName() == "terrain"):
            base.camera.setZ(entries[0].getSurfacePoint(render).getZ()+1.0)
        if (base.camera.getZ() < self.ralph.getZ() + 2.0):
            base.camera.setZ(self.ralph.getZ() + 2.0 -jmp)
            
        # The camera should look in ralph's direction,
        # but it should also try to stay horizontal, so look at
        # a floater which hovers above ralph's head.
        
        self.floater.setPos(self.ralph.getPos())
        self.floater.setZ(self.ralph.getZ() + 2.0-jmp)
        base.camera.lookAt(self.floater)

        return task.cont


w = World()
run()

