#########################################################################
# Description: 3D Bin Packing optimization algorithm: given a set of packages, optimize their transport in a set of boxs.
#
# Ref: Dube & Kanavathy. "Optimizing Three-Dimensional Bin Packing Through Simulation." Sixth IASTED International Conference Modelling, Simulation, and Optimization. 2006.
##########################################################################



# Classes
class Package:
    """
    Class representing a package with dimensions and weight.
    """
    def __init__(self, name, w, t, h, weight):
        self.__name = name
        self.__weight = weight
        self.__height = h
        self.__width = w
        self.__thickness = t
        self.__volume  = w * h * t
        self.__currentRotation = 0
        self.__coordinate = [0, 0, 0] # vertex position (Bottom Rear Left) of the Package in 3D space [width, thickness, height]

    def get_name(self):
        return self.__name

    def get_width(self):
        return self.__width

    def get_height(self):
        return self.__height

    def get_thickness(self):
        return self.__thickness

    def get_weight(self):
        return self.__weight

    def get_volume(self):
        return self.__volume

    def get_rotation(self, type):
        if   type == 0: return [self.__width, self.__thickness, self.__height]
        elif type == 1: return [self.__width, self.__height, self.__thickness]
        elif type == 2: return [self.__thickness, self.__height, self.__width]
        elif type == 3: return [self.__thickness, self.__width, self.__height]
        elif type == 4: return [self.__height, self.__width, self.__thickness]
        elif type == 5: return [self.__height, self.__thickness, self.__width]

    def set_rotation_type(self, type):
        self.__currentRotation = type

    def get_rotation_type(self):
        return self.__currentRotation

    def get_size(self):
        return self.get_rotation(self.__currentRotation)

    def set_coordinate(self, coordinate):
        self.__coordinate = coordinate

    def get_coordinate(self):
        return self.__coordinate

    def get_max_width(self):
        return self.__coordinate[0] + self.__width

    def get_max_thickness(self):
        return self.__coordinate[1] + self.__thickness

    def get_max_height(self):
        return self.__coordinate[2] + self.__height

class Box(Package):
    """
    Class representing a box with specific platform and weight limits.
    Inherits from Package.
    """
    def __init__(self, platform, name, w, t, h, weight,selfweight):
        self._Package__name = name
        self._Package__height = h
        self._Package__width = w
        self._Package__thickness = t
        self._Package__volume  = w * h * t 
        self.__weightLimit = weight  
        self.__selfweight  = selfweight        
        self.__loadedWeight = 0
        self.__packagesInside = []
        self.__packagesOutside = []
        self.__occupiedPivots = []
        self.__platform = platform

    def get_platform(self):
        return self.__platform

    def get_packed_packages(self):
        return self.__packagesInside

    def get_unpacked_packages(self):
        return self.__packagesOutside

    def get_occupied_pivots(self):
        return self.__occupiedPivots

    def set_occupied_pivot(self, pivot):
        self.__occupiedPivots.append(pivot)

    def add_packed_package(self, package):
        self.__packagesInside.append(package)

    def add_unpacked_package(self, package):
        self.__packagesOutside.append(package)

    def add_loaded_weight(self, weight):
        self.__loadedWeight += weight

    def get_loaded_weight(self):
        return self.__loadedWeight

    def get_weight_limit(self):
        return self.__weightLimit

    def get_self_weight(self):
        return self.__selfweight

    def get_available_weight(self):
        return self.__weightLimit - self.__loadedWeight

    def get_packed_volume(self):
        volume = 0
        for package in self.__packagesInside:
            volume += package.get_volume()
        return volume

    def get_available_volume(self):
        return self._Package__volume - self.get_packed_volume()

    def clear(self):
        self.__loadedWeight = 0
        self.__packagesInside = []
        self.__packagesOutside = []
        self.__occupiedPivots = []

    def pack(self, package, pivot):
        """
        Attempt to pack a package into the box at the given pivot.
        """
        for rotation in range(6):
            packageSize = package.get_rotation(rotation)
            if (self._Package__width - pivot[0]) < packageSize[0]:
                continue
            if (self._Package__thickness - pivot[1]) < packageSize[1]:
                continue
            if (self._Package__height - pivot[2]) < packageSize[2]:
                continue
            collided = False
            for packed in self.__packagesInside:
                packedCoordinate = packed.get_coordinate()
                if ((packedCoordinate[0] < (pivot[0] + packageSize[0]) and packed.get_max_width() > pivot[0]) and
                    (packedCoordinate[1] < (pivot[1] + packageSize[1]) and packed.get_max_thickness() > pivot[1]) and
                    (packedCoordinate[2] < (pivot[2] + packageSize[2]) and packed.get_max_height() > pivot[2])):
                    collided = True
                    break
            if not collided:
                package.set_rotation_type(rotation)          # success: change current package rotation
                package.set_coordinate(pivot)                # success: position the package at the pivot (Bottom Rear Left)
                self.set_occupied_pivot(pivot)               # success: position the package at the pivot
                self.add_packed_package(package)             # success: insert package into box's packed packages
                self.add_loaded_weight(package.get_weight()) # success: add the package weight to the load
                return True # if all checks are passed, the package is <= the available space
        return False # if no rotation returns True, then no rotation fits the package

# Packer
def packer(box, packages):
    """
    Attempt to pack all packages into the given box.
    """
    sorted_packages = sorted(packages, key=lambda p: (p.get_volume(), p.get_weight()), reverse=True)  # Sort packages by volume and weight
    for package in sorted_packages:
        packageFit = False

        if (box.get_available_weight() < package.get_weight()) or (box.get_available_volume() < package.get_volume()):
            box.add_unpacked_package(package)
            continue

        if len(box.get_packed_packages()) == 0:
            packageFit = box.pack(package, [0, 0, 0])
            if not packageFit:
                box.add_unpacked_package(package)  # if the package didn't fit in the empty box,
                continue                               # it is larger or heavier than the box
        
        # Pivot Selection: box loaded with at least one package
        else:
            pivots = get_pivots(box)
            for pivot in pivots:
                if pivot in box.get_occupied_pivots():
                    continue
                    
                packageFit = box.pack(package, pivot)  # if the package fits, its information is added to the box
                if packageFit:
                    break # if the package was packed, there's no need to check other pivots

        # If no attempt fit the package, it remains outside
        if not packageFit:
            box.add_unpacked_package(package)

def get_pivots(box):
    """
    Generate potential pivot points for placing new packages.
    """
    pivots = set()
    for packed in box.get_packed_packages():
        packedCoordinate = packed.get_coordinate()
        packedSize = packed.get_size()
        pivots.add((packedCoordinate[0] + packedSize[0], packedCoordinate[1], packedCoordinate[2]))  # [Bottom Rear Right]
        pivots.add((packedCoordinate[0], packedCoordinate[1] + packedSize[1], packedCoordinate[2]))  # [Bottom Front Left]
        pivots.add((packedCoordinate[0], packedCoordinate[1], packedCoordinate[2] + packedSize[2]))  # [Top Rear Left]
    return list(pivots)

# Classifier
def classifier(platforms, packages):
    """
    Classify the best box or combination of boxs to pack the packages.
    """
   # if not args.d:
   #     print("Smallest box that accommodates the maximum load:")
   # else:
    solution = []
    details  = []
    totalpercentage = 0
    for platform in platforms.keys():
    
        
        boxes = platforms.get(platform)
        boxes.sort(key=lambda box: box.get_volume())  # Sort boxes by volume
        unpackedPackages = packages
        i = 1000 # maximum 1000 boxes
        while i > 1: # Try multiple iterations to find the best fit
            i -= 1
            packagePercentage = {}
            packageCount = {}
            packageNames = {}
            unpackageNames = {}
            for box in boxes:
                box.clear()
            for box in boxes:
                packer(box, unpackedPackages)
                packagePercentage[box.get_name()] = (len(box.get_packed_packages()) / len(packages))  # Store the % of load carried for each box
                packageCount[box.get_name()] = (len(box.get_packed_packages()))                       # Store the raw count of load carried for each box
                packageNames[box.get_name()] = (box.get_packed_packages())                            # Store the packages loaded in each box
                unpackageNames[box.get_name()] = (box.get_unpacked_packages())                        # Store the packages not loaded in each box
                if len(box.get_packed_packages()) == len(packages):  # Early termination if all packages are packed
                    break

            bestOption = max(packagePercentage, key=packagePercentage.get)
            if(packagePercentage[bestOption]==0): break
            totalpercentage = totalpercentage + packagePercentage[bestOption]
            solution.append(f"{bestOption} | Packed: {(packagePercentage[bestOption]*100):.2f}%")
            details.append(f"Details")
            for box in boxes:
                if box.get_name() == bestOption:
                    solution.append(f"{box.get_width()} x {box.get_thickness()} x {box.get_height()}inches | Total Weight | {box.get_loaded_weight()+box.get_self_weight():.2f}lbs")
                    details.append(f"{box.get_width()} x {box.get_thickness()} x {box.get_height()}inches | Total Weight | {box.get_loaded_weight()+box.get_self_weight():.2f}lbs")
            lastpackgename=""  
            lastpackgeweight=0      
            qty = 0
            for package in packageNames[bestOption]:
                coord = package.get_coordinate()
                if package.get_name() == lastpackgename :
                   qty = qty +1
                   details.append(f"{package.get_name()} | {package.get_rotation_type()} | {coord[0]:.2f},{coord[1]:.2f},{coord[2]:.2f} | {package.get_width()} x {package.get_thickness()} x {package.get_height()}inches  | { package.get_weight():.2f}lbs")
                else:
                   if(qty == 0) :
                   	   lastpackgename = package.get_name()
                   	   lastpackgeweight = package.get_weight()
                   	   qty = 1
                   	   details.append(f"{package.get_name()} | {package.get_rotation_type()} | {coord[0]:.2f},{coord[1]:.2f},{coord[2]:.2f} | {package.get_width()} x {package.get_thickness()} x {package.get_height()}inches  | { package.get_weight():.2f}lbs")
                   else :
                   	   solution.append(f"{lastpackgename} | { lastpackgeweight:.2f}lbs x {qty}")
                   	   lastpackgename = package.get_name()
                   	   lastpackgeweight = package.get_weight()
                   	   qty = 1
                   	   details.append(f"{package.get_name()} | {package.get_rotation_type()} | {coord[0]:.2f},{coord[1]:.2f},{coord[2]:.2f} | {package.get_width()} x {package.get_thickness()} x {package.get_height()}inches  | { package.get_weight():.2f}lbs")
            if(qty): solution.append(f"{lastpackgename} | { lastpackgeweight:.2f}lbs x {qty}")
            unpackedPackages = unpackageNames[bestOption]
            if len(unpackageNames[bestOption]) == 0:
                break
    return solution,details,totalpercentage



